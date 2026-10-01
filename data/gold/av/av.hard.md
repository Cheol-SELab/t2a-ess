# Autonomous Vehicle Autonomous Operation Scenario (hard)

> Input text reverse-generated from all ground-truth information in Ground truth `av.gold.json`. The hard difficulty uses demonstrative expressions, omitted subjects, and complex sentences heavily, but preserves numbers, units, and individual actors so that they can be uniquely recovered from context.

This vehicle drives itself. In addition to the perception unit that reads the surroundings, the planning unit that lays out the way, the control unit that steers it along, and the drive unit that actually moves the wheels, a module that communicates with the outside, a system that looks after the battery, and even a screen that tells people the status are bound together into one body. Inside the aforementioned perception unit, a LiDAR, a camera, and a radar are housed together. Outside the car, the control side watches that status from afar, and on another side, the drained battery is refilled.

When the driver sent a signal saying "I'll hand it over now," the control unit brought up the autonomous mode. Soon that fact appeared on the screen as well, and in this way the agent of driving passed from hands to the system.

From then on it was a ceaseless repetition. When the raw signals scraped together by the three eyes up front were blended into one to draw a picture of the surroundings, the planning unit that received that picture drew the way to go. The control unit in turn translated that way into steering and acceleration-deceleration commands, and the drive unit moved accordingly without delay. This one round ran in the blink of an eye, about ten times per second. All the while, the communication module carried the car's condition over to the control side, and the other side watched it without missing anything.

Then something caught on the camera. It was a person crossing ahead. Hitting them was not an option. So the vehicle control module, without hesitation, performed emergency braking within a reaction time not exceeding 200 ms, that is, 0.2 s.

And not long after, it was detected that the LiDAR was not what it used to be. It was better not to push it. It was decided to go on in a degraded state, and stepping down from sound autonomy to one-level-lower autonomy, the speed was also held below 30 km/h.

In the meantime, the side that watched the battery measured the remaining amount, and the SoC was 18%. Having dropped below one fifth, that is, the 20%-or-less threshold, it had to be refilled to keep rolling. The planning unit re-set the way toward the charging station, and when the communication module asked for charging, it passed from the lowered autonomy to charging.

At length the other side charged the car. Where all of this was heading was, in the end, the task of bringing people to the destination without mishap.
