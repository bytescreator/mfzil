#include "ampController.h"

void dispatcher(Operation* opstring) {
    Operation returnData;

    switch (opstring->opcode) {
        case PING:
            returnData.opcode = PONG;

        case POWER_AMP:
            digitalWrite(AMP_PIN, HIGH);
            returnData.opcode = SUCCESS;

        case UNPOWER_AMP:
            digitalWrite(AMP_PIN, LOW);
            returnData.opcode = SUCCESS;
        
        case STATUS:
            returnData.portStatus = PORTB0;
            returnData.opcode = SUCCESS;
    }

    Serial.write((char*) &returnData, sizeof(returnData));
    Serial.write((char) 0x10);
}

void setup() {
    Serial.begin(9600);
    pinMode(AMP_PIN, OUTPUT);
}

void loop() {
    char* opstring = (char*) malloc(sizeof(buf));
    opstringLen = sizeof(buf);

    memset(buf, 0x00, sizeof(buf));
    memset(opstring, 0x00, opstringLen);

    opstringLen += (size_t) Serial.readBytesUntil((char) 0x10, buf, sizeof(buf));
    opstring = (char*) realloc(opstring, opstringLen);
    strncpy(opstring, buf, sizeof(buf));

    while(Serial.available()) {
        opstringLen += (size_t) Serial.readBytesUntil((char) 0x10, buf, sizeof(buf));
        opstring = (char*) realloc(opstring, opstringLen);
        strncpy(opstring, buf, sizeof(buf));
    }

    dispatcher((Operation*) opstring);

    free(opstring);
}
