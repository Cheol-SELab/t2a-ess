private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// Autonomous vehicle design ground truth scenario
// Generated from T2A-ESS by t2a_sysml.effbd.v0.3

#Performer
part 'Autonomous vehicle' : Performer;
#Performer
part 'Perception system' : Performer;
#Performer
part 'LiDAR sensor' : Performer;
#Performer
part 'Camera sensor' : Performer;
#Performer
part 'Radar sensor' : Performer;
#Performer
part 'Path planning module' : Performer;
#Performer
part 'Vehicle control module' : Performer;
#Performer
part 'Drive actuator' : Performer;
#Performer
part 'V2X communication module' : Performer;
#Performer
part 'Battery management system' : Performer;
#Performer
part 'HMI' : Performer;
#Performer
part 'Control center server' : Performer;
#Performer
part 'Charging station' : Performer;
#Performer
part 'Driver' : Performer;

#Function
action 'Autonomous vehicle autonomous operation scenario' {
    #Function
    action 'Autonomous driving start' {
        #Function
        action 'Activate autonomous driving mode';
        #Function
        action 'Display mode transition notification';

        fork 'New Start Concurrency_1';
        join 'New End Concurrency_1';

        allocate 'Activate autonomous driving mode' to 'Vehicle control module';
        allocate 'Display mode transition notification' to 'HMI';

        succession first start then 'New Start Concurrency_1';
        succession first 'Activate autonomous driving mode' then 'New End Concurrency_1';
        succession first 'Display mode transition notification' then 'New End Concurrency_1';
        succession first 'New Start Concurrency_1' then 'Activate autonomous driving mode';
        succession first 'New Start Concurrency_1' then 'Display mode transition notification';
        succession first 'New End Concurrency_1' then done;
    }
    #Function
    action 'Normal autonomous driving' {
        #Function
        action 'Collect sensor data' {
            out item 'Raw sensor data' : ItemOutputEdge;
        }
        #Function
        action 'Sensor fusion and environment perception' {
            in item 'Raw sensor data' : ItemInputEdge;
            out item 'Environment perception data' : ItemOutputEdge;
        }
        #Function
        action 'Generate driving path' {
            in item 'Environment perception data' : ItemInputEdge;
            out item 'Driving path' : ItemOutputEdge;
        }
        #Function
        action 'Generate control commands' {
            in item 'Driving path' : ItemInputEdge;
            out item 'Control commands' : ItemOutputEdge;
        }
        #Function
        action 'Execute control commands' {
            in item 'Control commands' : ItemInputEdge;
        }
        #Function
        action 'Transmit vehicle status report' {
            out item 'Vehicle status report' : ItemOutputEdge;
        }
        #Function
        action 'Monitor vehicle status';

        fork 'New Start Concurrency_2';
        join 'New End Concurrency_2';

        attribute 'While the autonomous driving state is maintained' : ScalarValues::Boolean;  // control: loop

        allocate 'Collect sensor data' to 'Perception system';
        allocate 'Sensor fusion and environment perception' to 'Perception system';
        allocate 'Generate driving path' to 'Path planning module';
        allocate 'Generate control commands' to 'Vehicle control module';
        allocate 'Execute control commands' to 'Drive actuator';
        allocate 'Transmit vehicle status report' to 'V2X communication module';
        allocate 'Monitor vehicle status' to 'Control center server';

        succession first start then 'New Start Concurrency_2';
        succession first 'Collect sensor data' if 'While the autonomous driving state is maintained' == true then 'Sensor fusion and environment perception';
        succession first 'Sensor fusion and environment perception' then 'Generate driving path';
        succession first 'Generate driving path' then 'Generate control commands';
        succession first 'Generate control commands' then 'Execute control commands';
        succession first 'Transmit vehicle status report' then 'Monitor vehicle status';
        succession first 'Execute control commands' then 'New End Concurrency_2';
        succession first 'Monitor vehicle status' then 'New End Concurrency_2';
        succession first 'New Start Concurrency_2' then 'Collect sensor data';
        succession first 'New Start Concurrency_2' then 'Transmit vehicle status report';
        succession first 'New End Concurrency_2' then done;

        flow from 'Collect sensor data'.'Raw sensor data' to 'Sensor fusion and environment perception'.'Raw sensor data';
        flow from 'Sensor fusion and environment perception'.'Environment perception data' to 'Generate driving path'.'Environment perception data';
        flow from 'Generate driving path'.'Driving path' to 'Generate control commands'.'Driving path';
        flow from 'Generate control commands'.'Control commands' to 'Execute control commands'.'Control commands';
    }
    #Function
    action 'Pedestrian detection and avoidance' {
        #Function
        action 'Detect pedestrian ahead';
        #Function
        action 'Emergency braking';

        attribute 'When a pedestrian ahead is detected' : ScalarValues::Boolean;  // control: decision

        allocate 'Detect pedestrian ahead' to 'Perception system';
        allocate 'Emergency braking' to 'Vehicle control module';

        succession first start then 'Detect pedestrian ahead';
        succession first 'Detect pedestrian ahead' if 'When a pedestrian ahead is detected' == true then 'Emergency braking';
        succession first 'Emergency braking' then done;
    }
    #Function
    action 'Sensor degradation response' {
        #Function
        action 'Switch to degraded mode';

        allocate 'Switch to degraded mode' to 'Vehicle control module';

        succession first start then 'Switch to degraded mode';
        succession first 'Switch to degraded mode' then done;
    }
    #Function
    action 'Return to charging station' {
        #Function
        action 'Measure battery SoC';
        #Function
        action 'Replan route to charging station' {
            out item 'Driving path' : ItemOutputEdge;
        }
        #Function
        action 'Transmit charging request' {
            out item 'Charging request' : ItemOutputEdge;
        }
        #Function
        action 'Charge vehicle';

        fork 'New Start Concurrency_3';
        join 'New End Concurrency_3';

        allocate 'Measure battery SoC' to 'Battery management system';
        allocate 'Replan route to charging station' to 'Path planning module';
        allocate 'Transmit charging request' to 'V2X communication module';
        allocate 'Charge vehicle' to 'Charging station';

        succession first start then 'New Start Concurrency_3';
        succession first 'Replan route to charging station' then 'Transmit charging request';
        succession first 'Transmit charging request' then 'Charge vehicle';
        succession first 'Measure battery SoC' then 'New End Concurrency_3';
        succession first 'Charge vehicle' then 'New End Concurrency_3';
        succession first 'New Start Concurrency_3' then 'Measure battery SoC';
        succession first 'New Start Concurrency_3' then 'Replan route to charging station';
        succession first 'New End Concurrency_3' then done;
    }

    item 'Raw sensor data';
    item 'Environment perception data';
    item 'Driving path';
    item 'Control commands';
    item 'Vehicle status report';
    item 'Charging request';

    succession first start then 'Autonomous driving start';
    succession first 'Autonomous driving start' then 'Normal autonomous driving';
    succession first 'Normal autonomous driving' then 'Pedestrian detection and avoidance';
    succession first 'Pedestrian detection and avoidance' then 'Sensor degradation response';
    succession first 'Sensor degradation response' then 'Return to charging station';
    succession first 'Return to charging station' then done;
}
