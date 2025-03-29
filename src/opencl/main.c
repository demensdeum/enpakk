#include <CL/cl.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <zlib.h>

#define BLOCK_SIZE 2
#define HASH_SIZE 1
#define CRC32_SIZE 4
#define MAX_CANDIDATES 300

#define CHECK_ERROR(err, msg) \
    if (err != CL_SUCCESS) { fprintf(stderr, "%s (%d)\n", msg, err); exit(1); }

uint8_t crc8(const uint8_t *data, size_t len) {
    uint8_t crc = 0x00;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80) crc = ((crc << 1) ^ 0x07) & 0xFF;
            else crc = (crc << 1) & 0xFF;
        }
    }
    return crc;
}

char *load_kernel_source(const char *filename) {
    FILE *f = fopen(filename, "r");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    size_t len = ftell(f);
    rewind(f);
    char *src = malloc(len + 1);
    fread(src, 1, len, f);
    src[len] = '\0';
    fclose(f);
    return src;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <input.enpakk> <output>\n", argv[0]);
        return 1;
    }

    FILE *fin = fopen(argv[1], "rb");
    if (!fin) { perror("fopen input"); return 1; }

    FILE *fout = fopen(argv[2], "wb");
    if (!fout) { perror("fopen output"); fclose(fin); return 1; }

    // Read CRC32
    uint8_t crc_buf[CRC32_SIZE];
    fread(crc_buf, 1, CRC32_SIZE, fin);
    uint32_t expected_crc = crc_buf[0] | (crc_buf[1] << 8) | (crc_buf[2] << 16) | (crc_buf[3] << 24);

    // Read hash data
    fseek(fin, 0, SEEK_END);
    long file_size = ftell(fin);
    fseek(fin, CRC32_SIZE, SEEK_SET);
    size_t hash_data_len = file_size - CRC32_SIZE;
    uint8_t *hash_data = malloc(hash_data_len);
    fread(hash_data, 1, hash_data_len, fin);
    fclose(fin);

    // Build candidate list
    uint8_t *candidates[256][MAX_CANDIDATES];
    size_t candidate_counts[256] = {0};
    for (int b1 = 0; b1 < 256; b1++) {
        for (int b2 = 0; b2 < 256; b2++) {
            uint8_t block[2] = { b1, b2 };
            uint8_t h = crc8(block, 2);
            if (candidate_counts[h] < MAX_CANDIDATES) {
                uint8_t *copy = malloc(2);
                memcpy(copy, block, 2);
                candidates[h][candidate_counts[h]++] = copy;
            }
        }
    }

    // Flatten candidate array
    int *block_indices = malloc(sizeof(int) * hash_data_len);
    int offset = 0;
    for (size_t i = 0; i < hash_data_len; i++) {
        block_indices[i] = offset;
        offset += candidate_counts[hash_data[i]];
    }

    int total_blocks = offset;
    uint8_t *flat_blocks = malloc(2 * total_blocks);
    offset = 0;
    for (size_t i = 0; i < hash_data_len; i++) {
        uint8_t h = hash_data[i];
        for (size_t j = 0; j < candidate_counts[h]; j++) {
            memcpy(&flat_blocks[(offset + j) * 2], candidates[h][j], 2);
        }
        offset += candidate_counts[h];
    }

    // OpenCL setup
    cl_platform_id platform;
    cl_device_id device;
    cl_context context;
    cl_command_queue queue;
    cl_program program;
    cl_kernel kernel;
    cl_int err;

    CHECK_ERROR(clGetPlatformIDs(1, &platform, NULL), "clGetPlatformIDs");
    CHECK_ERROR(clGetDeviceIDs(platform, CL_DEVICE_TYPE_GPU, 1, &device, NULL), "clGetDeviceIDs");
    context = clCreateContext(NULL, 1, &device, NULL, NULL, &err); CHECK_ERROR(err, "clCreateContext");
    queue = clCreateCommandQueue(context, device, 0, &err); CHECK_ERROR(err, "clCreateCommandQueue");

    char *kernel_src = load_kernel_source("decompress.cl");
    program = clCreateProgramWithSource(context, 1, (const char**)&kernel_src, NULL, &err); CHECK_ERROR(err, "clCreateProgram");
    err = clBuildProgram(program, 1, &device, NULL, NULL, NULL);
    if (err != CL_SUCCESS) {
        char log[2048];
        clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, sizeof(log), log, NULL);
        fprintf(stderr, "Build log:\n%s\n", log);
        exit(1);
    }
    kernel = clCreateKernel(program, "brute_crc32", &err); CHECK_ERROR(err, "clCreateKernel");

    int outputs_to_try = 100000;
    int buffer_size = hash_data_len * 2;
    uint8_t *output_data = calloc(outputs_to_try * buffer_size, 1);
    uint8_t *found_output = calloc(buffer_size, 1);
    int found_flag = 0;

    cl_mem buf_blocks = clCreateBuffer(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, 2 * total_blocks, flat_blocks, &err);
    cl_mem buf_indices = clCreateBuffer(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, sizeof(int) * hash_data_len, block_indices, &err);
    cl_mem buf_outputs = clCreateBuffer(context, CL_MEM_WRITE_ONLY, outputs_to_try * buffer_size, NULL, &err);
    cl_mem buf_found_flag = clCreateBuffer(context, CL_MEM_READ_WRITE | CL_MEM_COPY_HOST_PTR, sizeof(int), &found_flag, &err);
    cl_mem buf_found_output = clCreateBuffer(context, CL_MEM_WRITE_ONLY, buffer_size, NULL, &err);

    CHECK_ERROR(err, "clCreateBuffer");

    CHECK_ERROR(clSetKernelArg(kernel, 0, sizeof(cl_mem), &buf_blocks), "arg0");
    CHECK_ERROR(clSetKernelArg(kernel, 1, sizeof(cl_mem), &buf_indices), "arg1");
    CHECK_ERROR(clSetKernelArg(kernel, 2, sizeof(int), &hash_data_len), "arg2");
    CHECK_ERROR(clSetKernelArg(kernel, 3, sizeof(int), &outputs_to_try), "arg3");
    CHECK_ERROR(clSetKernelArg(kernel, 4, sizeof(uint32_t), &expected_crc), "arg4");
    CHECK_ERROR(clSetKernelArg(kernel, 5, sizeof(cl_mem), &buf_outputs), "arg5");
    CHECK_ERROR(clSetKernelArg(kernel, 6, sizeof(cl_mem), &buf_found_flag), "arg6");
    CHECK_ERROR(clSetKernelArg(kernel, 7, sizeof(cl_mem), &buf_found_output), "arg7");

    size_t global_work_size = outputs_to_try;
    CHECK_ERROR(clEnqueueNDRangeKernel(queue, kernel, 1, NULL, &global_work_size, NULL, 0, NULL, NULL), "enqueue");

    clFinish(queue);

    clEnqueueReadBuffer(queue, buf_found_flag, CL_TRUE, 0, sizeof(int), &found_flag, 0, NULL, NULL);
    if (found_flag) {
        clEnqueueReadBuffer(queue, buf_found_output, CL_TRUE, 0, buffer_size, found_output, 0, NULL, NULL);
        fwrite(found_output, 1, buffer_size, fout);
        printf("[✓] Decompression complete!\n");
    } else {
        printf("[X] Failed to find valid CRC match.\n");
    }

    // Cleanup
    for (int h = 0; h < 256; h++) {
        for (size_t j = 0; j < candidate_counts[h]; j++) {
            free(candidates[h][j]);
        }
    }
    free(hash_data);
    free(flat_blocks);
    free(block_indices);
    free(output_data);
    free(found_output);
    free(kernel_src);
    clReleaseMemObject(buf_blocks);
    clReleaseMemObject(buf_indices);
    clReleaseMemObject(buf_outputs);
    clReleaseMemObject(buf_found_flag);
    clReleaseMemObject(buf_found_output);
    clReleaseKernel(kernel);
    clReleaseProgram(program);
    clReleaseCommandQueue(queue);
    clReleaseContext(context);
    fclose(fout);
    return 0;
}
