# Motor Imagery and Fine Motor Laterality - Hancock 2023

This repository contains the experiment code for a study on how motor imagery affects the lateralization of fine-motor learning. The purpose of the task is to measure how well learning on a challenging fine-motor task transfers from one hand to the other, and specifically test whether the *amount* of lateral transfer is affected by how the task is practiced (physically or via motor imagery).

![MotorMapping](task.gif)

On each trial, a target will appear on the screen at a random distance and angle from fixation after a random delay. Once the target appears, the task of the participant is to move the cursor (translucent red circle) from the middle of the screen to be hovering over the target (small white dot) using the joystick on a gamepad. While over the target, the participant then needs to squeeze one of the gamepad's rear triggers to end the trial.

The experiment has three phases: a practice phase, a training phase, and a testing phase:

* The **practice phase** is the same for all particpants (a small number of physical practice trials to familiarize people with the task). For all trials, the cursor is controlled with the participant's dominant hand.
* The **training phase** differs depending on the experiment condition: some people continue to practice the task physically, and some are asked to practice the task using motor imagery. Like the first phase, the cursor is controlled on all trials by the participant's dominant hand.
* During the **testing phase**, all participants perform the task physically, except that the cursor now alternates semi-randomly between red and blue. When the cursor is *red*, the cursor is controlled with the participant's dominant hand like before. When the cursor is *blue*, the cursor is controlled with the *opposite* stick using the participant's non-dominant hand. 

Reaction times to targets are recorded, allowing the degree and duration of the mapping-change impairment in the final block to be measured and compared across groups.

## Requirements

This task is programmed in Python 3.9 using the [KLibs framework](https://github.com/a-hurst/klibs). It has been developed and tested on recent versions of macOS and Linux, but should also work without issue on Windows systems.

To use the task with a gamepad (as intended), you will also need a USB or wireless controller that is supported by your computer. The task has been tested with Microsoft Xbox 360 wired controllers as well as Sony DualShock 4 controllers via Bluetooth, but most gamepads that provide a joystick and rear triggers should work with the task. If no gamepad is available, mouse movement/clicking will be used in place of the joystick/triggers (respectively).


## Getting Started

### Installation

To download a copy of the task, you can grab a .zip archive of the current code [here](https://github.com/LBRF-Projects/Laterality_Hancock2023/archive/refs/heads/main.zip). Alternatively, you can clone this repository to your computer using Git by opening a terminal in your destination folder and running the following command:

```
git clone https://github.com/LBRF-Projects/Laterality_Hancock2023.git
```

#### Option 1: Pipenv Installation

To install the task and its dependencies in a self-contained Python environment, run the following commands in a terminal window inside the same folder as this README:

```bash
pip install pipenv
pipenv install
```
These commands should create a fresh environment the task with all its dependencies installed. Note that to run commands using this environment, you will need to prefix them with `pipenv run` (e.g. `pipenv run klibs run 15.6`).

#### Option 2: Global Installation

Alternatively, to install the dependencies for the task in your global Python environment, run the following commands in a terminal window:

```bash
pip install https://github.com/a-hurst/klibs/releases/latest/download/klibs.tar.gz
pip install pyusb
pip install libusb_package # Only required for 360 controller support on macOS
```

### Running the Experiment

This task is a KLibs experiment, meaning that it is run using the `klibs` command at the terminal (running the 'experiment.py' file using Python directly will not work).

To run the experiment, navigate to the task folder in a terminal and run `klibs run [screensize]`, replacing `[screensize]` with the diagonal size of your display in inches (e.g. `klibs run 21.5` for a 21.5-inch monitor). Note that the stimulus sizes for the study assume that a) the screen size for the monitor has been specified accurately, and b) that participants are seated approximately 57 cm from the screen.

If you just want to test the program out for yourself and skip demographics collection, you can add the `-d` flag to the end of the command to launch the experiment in development mode.

#### Optional Settings

This task has two possible between-subjects conditions: physical practice (PP) and motor imagery (MI).

To choose which condition to run, launch the experiment with the `--condition` or `-c` flag, followed by either `PP` or `MI`. For example, if you wanted to run a participant in the motor imagery condition on a computer with a 15.6-inch monitor, you would run 

```
klibs run 15.6 --condition MI
```

If no condition is manually specified, the experiment program will default to physical practice.
 

### Exporting Data

To export data from the task, simply run

```
klibs export
```

while in the root of the task directory. This will export the trial data for each participant into individual tab-separated text files in the project's `ExpAssets/Data` subfolder.

KVIQ scores and raw gamepad joystick data can likewise be exported from the data base with `klibs export -t kviq` and `klibs export -t gamepad`, respectively.
