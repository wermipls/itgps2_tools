#include "RageSoundReader_MP3.h"
#include <cstdio>
#include <cstdint>

#ifdef _WIN32
    #include <io.h>
    #include <fcntl.h>
#endif

struct wav 
{
    uint8_t  riff[4] = {'R','I','F','F'};
    uint32_t fsize;
    uint8_t  wave[4] = {'W','A','V','E'};

    uint8_t  fmt[4] = {'f','m','t',' '};
    uint32_t fmt_size;
    uint16_t type;
    uint16_t channels;
    uint32_t rate;
    uint32_t byterate;
    uint16_t frame_size;
    uint16_t bit_depth;
    uint8_t  data[4] = {'d','a','t','a'};
    uint32_t data_size;
};

int main(int argc, char *argv[])
{
    bool is_pipe_out = false;

    if (argc == 2) { 
        is_pipe_out = true;
    } else if (argc == 3) {
        // file out
    } else {
        printf("off me nut"); 
        return -1;
    }

    FILE *b = fopen(argv[1], "rb");
    if (b == NULL) {
        return -2;
    }

    RageSoundReader_MP3 mp3 = RageSoundReader_MP3();

    if (mp3.Open(b)) {
        return -3;
    }

    struct wav h;

    h.fmt_size = 16;
    h.type = 1;
    h.bit_depth = 16;
    h.channels = mp3.GetNumChannels();
    h.rate = mp3.GetSampleRate();
    h.frame_size = 2 * h.channels;
    h.byterate = h.frame_size * h.rate;

    int16_t buf[16*1024];

    if (is_pipe_out) {
        int i;
        #ifdef _WIN32
            _setmode(fileno(stdout), _O_BINARY);
        #endif
        
        fwrite((char *)&h, sizeof(h), 1, stdout);

        while ((i = mp3.Read(buf, 2048)) > 0) {
            fwrite((char *)buf, sizeof(int16_t), i * mp3.GetNumChannels(), stdout);
        }

        fclose(b);
        fflush(stdout);
    } else {
        FILE *a = fopen(argv[2], "wb");
        if (a == NULL) {
            return -4;
        }

        fwrite((char *)&h, sizeof(h), 1, a);

        int i;
        size_t bytes_total = 0;
        while ((i = mp3.Read(buf, 2048)) > 0) {
            bytes_total += fwrite((char *)buf, sizeof(int16_t), i * mp3.GetNumChannels(), a);
        }

        h.fsize = bytes_total - 8;
        h.data_size = bytes_total - 44;

        fseek(a, 0, SEEK_SET);

        fwrite((char *)&h, sizeof(h), 1, a);

        fclose(b);
        fclose(a);
    }

    return 0;
}