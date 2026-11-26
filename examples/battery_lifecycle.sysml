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
}

implementation C-BATT-THERMAL-CONTROL {
  revision = 1;
  sourceBehavior = "B-BATT-THERMAL-CONTROL@1";
  language = "Python";
  entryPoint = "generate_heater_command";
  targetPlatform = "embedded";
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
}

test scenario TC-S-COLD-START {
  revision = 1;
  purpose = "Cold battery recovers into the normal temperature band.";
  initialTemperatureC = 18.0;
  ambientTemperatureC = 20.0;
  steps = 50;
}

evidence E-BATT-THERMAL {
  revision = 1;
  result = "pass";
  summary = "Battery thermal lifecycle verification passed.";
  requirement = "R-BATT-THERMAL@1";
  behavior = "B-BATT-THERMAL-CONTROL@1";
}
