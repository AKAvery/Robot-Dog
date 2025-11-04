#pragma once
#include <Arduino.h>

// ==== set this to 8 now, 12 when you wire hip-yaw ====
#define NUM_SERVOS 8

// Pins for first 8 channels (expand when you go 12)
static const uint8_t SERVO_PINS[NUM_SERVOS] = {13,12,14,27,26,25,33,32};

// Optional: per-servo center offsets (degrees) and reverse flags
static const int8_t  SERVO_OFFSET[NUM_SERVOS] = {0,0,0,0,0,0,0,0};
static const bool    SERVO_REVERSE[NUM_SERVOS]= {false,true,true,true,false,true,true,true};
