#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    FILE *input;
    char **target_argv = NULL;
    size_t target_argc = 0;
    size_t target_capacity = 0;

    if (argc != 2 || argv[1][0] != '/') {
        fprintf(stderr, "usage: %s TARGET_ARGV_FILE\n", argv[0]);
        return 64;
    }
    input = fopen(argv[1], "rb");
    if (input == NULL) {
        perror("fopen target argv");
        return 1;
    }
    for (;;) {
        char *argument = NULL;
        size_t argument_capacity = 0;
        ssize_t length = getdelim(&argument, &argument_capacity, '\0', input);

        if (length < 0) {
            free(argument);
            break;
        }
        if (argument[length - 1] != '\0') {
            fprintf(stderr, "target argv file has an unterminated argument\n");
            free(argument);
            fclose(input);
            return 65;
        }
        if (target_argc + 1 >= target_capacity) {
            size_t next_capacity = target_capacity == 0 ? 16 : target_capacity * 2;
            char **next_argv = realloc(target_argv, next_capacity * sizeof(*next_argv));

            if (next_argv == NULL) {
                perror("realloc target argv");
                free(argument);
                fclose(input);
                return 1;
            }
            target_argv = next_argv;
            target_capacity = next_capacity;
        }
        target_argv[target_argc++] = argument;
    }
    if (ferror(input)) {
        perror("read target argv");
        fclose(input);
        return 1;
    }
    fclose(input);
    if (target_argc == 0 || target_argv[0][0] != '/') {
        fprintf(stderr, "target argv must start with an absolute executable path\n");
        return 65;
    }
    target_argv[target_argc] = NULL;
    execv(target_argv[0], target_argv);
    fprintf(stderr, "execv %s: %s\n", target_argv[0], strerror(errno));
    return 1;
}
