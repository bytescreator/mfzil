#define AMP_PIN 8
#define PING 0
#define PONG 1
#define POWER_AMP 3
#define UNPOWER_AMP 4
#define STATUS 5

#define SUCCESS 255
#define FAILURE 127
#define ERROR 128

struct Operation {
    uint8_t opcode;
    uint8_t portStatus;
};

char opstring[sizeof(Operation)];
