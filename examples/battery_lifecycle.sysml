package 'Battery Thermal Control' {
    private import ScalarValues::*;

    part def SafetyEngineer;

    concern def BatteryThermalSafetyConcern {
        doc /* The battery temperature shall remain within safe operating limits and a sensor fault shall force safe-off. */
        subject battery : Battery;
        stakeholder safetyEngineer : SafetyEngineer;
    }

    requirement def <'BT-1'> BatteryTemperatureRequirement {
        doc /* The battery shall remain between 20 and 30 degrees Celsius and enter safe-off after a sensor fault. */
        subject battery : Battery;
        attribute minTemperatureC : Real = 20.0;
        attribute maxTemperatureC : Real = 30.0;
        require constraint {
            battery.temperatureC >= minTemperatureC and
            battery.temperatureC <= maxTemperatureC
        }
    }

    part def Battery {
        attribute temperatureC : Real;
        attribute sensorValid : Boolean;
    }

    port def TemperaturePort {
        out temperatureC : Real;
        out sensorValid : Boolean;
    }

    port def HeaterPort {
        in heaterCommand : String;
    }

    interface def ThermalInterface {
        end sensorEnd : TemperaturePort;
        end controllerEnd : ~HeaterPort;
    }

    action def GenerateHeaterCommand {
        in temperatureC : Real;
        in sensorValid : Boolean;
        out heaterCommand : String;
    }

    part def TemperatureSensor {
        port temperaturePort : TemperaturePort;
    }

    part def ThermalController {
        port temperaturePort : ~TemperaturePort;
        port heaterPort : HeaterPort;
        action generateHeaterCommand : GenerateHeaterCommand;
    }

    part def Heater {
        port heaterPort : ~HeaterPort;
    }

    part battery : Battery;
    part sensor : TemperatureSensor;
    part controller : ThermalController;
    part heater : Heater;

    interface batteryThermalInterface : ThermalInterface
        connect sensor.temperaturePort to controller.temperaturePort;

    allocate controller to battery;
    allocate controller.generateHeaterCommand to controller;

    requirement temperatureControl : BatteryTemperatureRequirement {
        subject battery = battery;
    }

    verification def BatteryThermalTest {
        subject testBattery : Battery;
        objective {
            verify temperatureControl;
        }
    }

    verification batteryThermalTest : BatteryThermalTest {
        subject testBattery = battery;
    }
}
