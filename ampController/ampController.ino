#include "ampController.h"

void dispatcher(Operation* opstring) {
    Operation returnData;

    switch (opstring->opcode) {
        case PING:
            returnData.opcode = PONG;
            break;

        case POWER_AMP:
            digitalWrite(AMP_PIN, HIGH);
            returnData.opcode = SUCCESS;
            break;

        case UNPOWER_AMP:
            digitalWrite(AMP_PIN, LOW);
            returnData.opcode = SUCCESS;
            break;
        
        case STATUS:
            returnData.portStatus = PORTB0;
            returnData.opcode = SUCCESS;
            break;
        
        default:
            returnData.opcode = ERROR;
            break;
    }

    Serial.write((char*) &returnData, sizeof(Operation));
    Serial.flush();
}

void setup() {
    Serial.begin(9600);
    while(!Serial) {};
    pinMode(AMP_PIN, OUTPUT);
}

void loop() {
    memset(opstring, 0x00, sizeof(Operation));

    if (Serial.readBytes(opstring, sizeof(Operation)) != sizeof(opstring)) return;
    dispatcher((Operation*) opstring);
}
