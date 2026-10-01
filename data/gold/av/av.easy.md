# Autonomous Vehicle Autonomous Operation Scenario (easy)

> Input text reverse-generated from all ground-truth information in Ground truth `av.gold.json`. The easy difficulty is written explicitly so that it corresponds almost 1:1 to the slots.

The autonomous vehicle consists of a perception system, a path planning module, a vehicle control module, a drive actuator, a V2X communication module, a battery management system, and an HMI. The perception system includes a LiDAR sensor, a camera sensor, and a radar sensor.

Outside the vehicle, there are a control center server that monitors the vehicle status and a charging station that charges the battery.

When the driver requests autonomous driving activation, the vehicle control module activates the autonomous driving mode and the HMI displays the autonomous driving mode transition. Accordingly, the vehicle transitions from the manual driving state to the normal autonomous driving state.

In the normal autonomous driving state, the perception system collects raw sensor data from the LiDAR, camera, and radar, and fuses it to generate environment perception data. This perception loop repeats at a 10 Hz cycle.

The path planning module generates a driving path using the environment perception data.

The vehicle control module generates steering/acceleration-deceleration control commands from the driving path, and the drive actuator executes the control commands.

The V2X communication module transmits the vehicle status report to the control center server, and the control center server monitors the vehicle status.

The camera sensor of the perception system detects a pedestrian ahead, and a pedestrian detection event occurs.

To avoid a collision, the vehicle control module performs emergency braking within 200 ms.

The perception system detects a LiDAR reliability degradation, and a LiDAR fault event occurs.

For safety, the vehicle control module switches to the degraded mode, the vehicle transitions from the normal autonomous driving state to the degraded autonomous driving state, and the speed is limited to 30 km/h or less.

The battery management system measures the battery SoC, the SoC is confirmed to be 18%, and a low-power event of 20% or less occurs.

To secure driving range, the path planning module replans the route to the charging station, the V2X communication module requests charging, and the vehicle transitions from the degraded autonomous driving state to the charging state.

The charging station charges the vehicle. The goal of this scenario is for the vehicle to arrive safely at the destination.
