package org.github.michaellrowley.sysmlqvt.template;

public final class SysMLTemplateLibrary {
    public String batteryLifecycle() {
        return """
package battery;

stakeholder need N-BATT-THERMAL {
  statement = "Keep the battery within 20 to 30 degrees Celsius during normal operation.";
  rationale = "Protect battery lifetime and prevent unsafe heater operation.";
  acceptanceCriteria = ["Normal-operation temperature remains between 20C and 30C.", "A sensor fault produces SAFE_OFF."];
  requirementId = "R-BATT-THERMAL";
}

requirement R-BATT-THERMAL {
  revision = 1;
  sourceNeed = "N-BATT-THERMAL@1";
  statement = "Keep the battery within 20 to 30 degrees Celsius during normal operation.";
  rationale = "Protect battery lifetime and prevent unsafe heater operation.";
  acceptanceCriteria = ["Normal-operation temperature remains between 20C and 30C.", "A sensor fault produces SAFE_OFF."];
}

part def BatteryPack;
part def TemperatureSensor;
part def ThermalController;
part def Heater;

behavior B-BATT-THERMAL-CONTROL {
  revision = 1;
  requirement = "R-BATT-THERMAL@1";
  kind = "state_machine";
  entryPoint = "generate_heater_command";
  initialState = "HOLD";
  states = ["HEAT", "HOLD", "SAFE_OFF"];
  heatBelowC = 24.0;
  offAboveC = 26.0;
  safeOffOnSensorFault = true;
  functionCalls = ["CALL-GENERATE-HEATER-COMMAND"];
  communications = ["COMM-TEMPERATURE-SENSOR", "COMM-HEATER-COMMAND"];
  schedules = ["SCH-THERMAL-CONTROL"];
}

interface IF-BATT-THERMAL-CONTROL {
  revision = 1;
  name = "BatteryThermalInterface";
  requirement = "R-BATT-THERMAL@1";
  architecture = "ThermalController@1";
  protocol = "CAN";
}

port P-TEMPERATURE-IN {
  revision = 1;
  name = "temperature_in";
  interface = "IF-BATT-THERMAL-CONTROL@1";
  direction = "in";
  protocol = "CAN";
}

port P-HEATER-OUT {
  revision = 1;
  name = "heater_out";
  interface = "IF-BATT-THERMAL-CONTROL@1";
  direction = "out";
  protocol = "CAN";
}

connection CONN-BATT-THERMAL {
  revision = 1;
  source = "P-TEMPERATURE-IN@1";
  target = "P-HEATER-OUT@1";
  transport = "CAN";
}

function call CALL-GENERATE-HEATER-COMMAND {
  revision = 1;
  behavior = "B-BATT-THERMAL-CONTROL@1";
  functionName = "generate_heater_command";
  target = "ThermalController";
  synchronous = true;
  timeoutMs = 10;
  returnBinding = "heaterCommand";
}

communication COMM-TEMPERATURE-SENSOR {
  revision = 1;
  behavior = "B-BATT-THERMAL-CONTROL@1";
  kind = "subscription";
  direction = "in";
  channel = "battery.temperature";
  protocol = "CAN";
  payloadType = "TemperatureReading";
}

communication COMM-HEATER-COMMAND {
  revision = 1;
  behavior = "B-BATT-THERMAL-CONTROL@1";
  kind = "command";
  direction = "out";
  channel = "heater.command";
  protocol = "CAN";
  payloadType = "HeaterCommand";
}

schedule SCH-THERMAL-CONTROL {
  revision = 1;
  behavior = "B-BATT-THERMAL-CONTROL@1";
  kind = "cyclic";
  periodMs = 100;
  deadlineMs = 100;
  wcetMs = 5;
  priority = 50;
  entryPoint = "generate_heater_command";
}

implementation C-BATT-THERMAL-CONTROL {
  revision = 1;
  sourceBehavior = "B-BATT-THERMAL-CONTROL@1";
  language = "Python";
  entryPoint = "generate_heater_command";
  targetPlatform = "embedded";
}

allocation AL-BATT-THERMAL-CONTROL {
  revision = 1;
  sourceRef = "B-BATT-THERMAL-CONTROL@1";
  targetRef = "ThermalController@1";
}

deployment DP-BATT-THERMAL-CONTROL {
  revision = 1;
  componentRef = "B-BATT-THERMAL-CONTROL@1";
  targetRef = "ThermalController@1";
  environment = "battery-controller-node";
  runtime = "bare-metal";
}

verification plan VP-BATT-THERMAL {
  revision = 1;
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
  implementation = "C-BATT-THERMAL-CONTROL@1";
  strategy = "requirements-driven component and scenario verification";
}

test component TC-C-LOW {
  revision = 1;
  purpose = "Low temperature requests heat.";
  temperatureC = 20.0;
  sensorValid = true;
  expected = "HEAT";
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
}

test component TC-C-HIGH {
  revision = 1;
  purpose = "High temperature turns the heater off.";
  temperatureC = 32.0;
  sensorValid = true;
  expected = "OFF";
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
}

test component TC-C-DEADBAND {
  revision = 1;
  purpose = "Deadband preserves the prior state.";
  temperatureC = 25.0;
  sensorValid = true;
  expected = "HOLD";
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
}

test component TC-C-SENSOR-FAULT {
  revision = 1;
  purpose = "Sensor fault forces safe-off.";
  temperatureC = 25.0;
  sensorValid = false;
  expected = "SAFE_OFF";
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
}

test scenario TC-S-COLD-START {
  revision = 1;
  purpose = "Cold battery recovers into the normal temperature band.";
  initialTemperatureC = 18.0;
  ambientTemperatureC = 20.0;
  steps = 50;
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
}

test scenario TC-S-HOT-AMBIENT {
  revision = 1;
  purpose = "Hot ambient conditions cool below the upper limit.";
  initialTemperatureC = 32.0;
  ambientTemperatureC = 28.0;
  steps = 50;
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
}

test scenario TC-S-SENSOR-LOSS {
  revision = 1;
  purpose = "Sensor loss forces safe-off.";
  initialTemperatureC = 25.0;
  ambientTemperatureC = 25.0;
  steps = 50;
  faultStep = 10;
  requireSafeOff = true;
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
}

evidence E-BATT-THERMAL {
  revision = 1;
  result = "pass";
  summary = "Battery thermal lifecycle verification passed.";
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
  implementation = "C-BATT-THERMAL-CONTROL@1";
  verificationPlan = "VP-BATT-THERMAL@1";
}
""";
    }

    public String genericNeed() {
        return """
package continuity;

stakeholder need N-SYSTEM {
  statement = "Describe the stakeholder need.";
  rationale = "Describe why the need matters.";
  acceptanceCriteria = ["Define observable acceptance criteria."];
  requirementId = "R-SYSTEM";
}

requirement R-SYSTEM {
  revision = 1;
  sourceNeed = "N-SYSTEM@1";
  statement = "Describe the derived requirement.";
  rationale = "Describe the requirement rationale.";
  acceptanceCriteria = ["Define one or more acceptance criteria."];
}

behavior B-SYSTEM {
  revision = 1;
  requirement = "R-SYSTEM@1";
  kind = "state_machine";
  entryPoint = "main";
  states = ["RUNNING", "FAULT"];
}
""";
    }
}
