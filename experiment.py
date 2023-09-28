# -*- coding: utf-8 -*-

__author__ = "Austin Hurst"

from math import sqrt
from copy import copy
from random import randrange, choice, shuffle
from ctypes import c_int, byref

import sdl2
import klibs
from klibs import P
from klibs.KLExceptions import TrialException
from klibs.KLGraphics import fill, flip, blit
from klibs.KLGraphics import KLDraw as kld
from klibs.KLEventQueue import flush, pump
from klibs.KLUtilities import angle_between, point_pos, deg_to_px, px_to_deg
from klibs.KLUtilities import line_segment_len as linear_dist
from klibs.KLTime import CountDown, precise_time
from klibs.KLCommunication import message
from klibs.KLUserInterface import (
    any_key, mouse_pos, ui_request, hide_cursor, smart_sleep,
)

from KVIQ import KVIQ
from gamepad import gamepad_init, button_pressed
from gamepad_usb import get_all_controllers

# Define colours for use in the experiment
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
MIDGREY = (128, 128, 128)
TRANSLUCENT_RED = (255, 0, 0, 96)
TRANSLUCENT_BLUE = (0, 0, 255, 96)

# Define constants for working with gamepad data
AXIS_MAX = 32768
TRIGGER_MAX = 32767


class MotorMapping(klibs.Experiment):

    def setup(self):

        # Prior to starting the task, run through the KVIQ
        self.handedness = self.db.select(
            'participants', columns=['handedness'], where={'id': P.participant_id}
        )[0][0]
        if P.run_kviq:
            self.txtm.add_style('title', '0.75deg')
            kviq = KVIQ(self.handedness == "l")
            responses = kviq.run()
            for movement, dat in responses.items():
                dat['participant_id'] = P.participant_id
                dat['movement'] = movement
                self.db.insert(dat, table='kviq') 

        # Initialize stimulus sizes and layout
        screen_h_deg = (P.screen_y / 2.0) / deg_to_px(1.0)
        fixation_size = deg_to_px(0.5)
        fixation_thickness = deg_to_px(0.06)
        self.cursor_size = deg_to_px(P.cursor_size)
        self.target_size = deg_to_px(0.3)
        self.target_dist_min = deg_to_px(3.0)
        self.target_dist_max = deg_to_px(8.0)
        self.lower_middle = (P.screen_c[0], int(P.screen_y * 0.75))
        self.msg_loc = (P.screen_c[0], int(P.screen_y * 0.4))

        # Initialize task stimuli
        self.cursor = kld.Ellipse(self.cursor_size, fill=TRANSLUCENT_RED)
        self.cursor_nd = kld.Ellipse(self.cursor_size, fill=TRANSLUCENT_BLUE)
        self.target = kld.Ellipse(self.target_size, fill=WHITE)
        self.fixation = kld.FixationCross(
            fixation_size, fixation_thickness, rotation=45, fill=WHITE
        )
        if P.development_mode and P.show_gamepad_debug:
            self.txtm.add_style('debug', '0.3deg')

        # Initialize gamepad (if present)
        self.gamepad = None
        gamepad_init()
        controllers = get_all_controllers()
        if len(controllers):
            self.gamepad = controllers[0]
            self.gamepad.initialize()
            print(self.gamepad._info)

        # Define error messages for the task
        dominant = "left" if self.handedness == "l" else "right"
        nondominant = "right" if self.handedness == "l" else "left"
        err_txt = {
            "too_soon": (
                "Too soon!\nPlease wait for the target to appear before responding."
            ),
            "too_slow": "Too slow!\nPlease try to respond faster.",
            "start_triggers": (
                "Please fully release the triggers before the start of each trial."
            ),
            "stick_mi": (
                "Joystick moved!\n"
                "Please try to only *imagine* moving the stick over the target\n"
                "without actually performing the movement."
            ),
            "stick_cc": (
                "Joystick moved!\n"
                "Please pull the trigger as soon as you see the target, without\n"
                "moving the cursor."
            ),
            "wrong_hand": (
                "Wrong hand!\n"
                f"Please use the {dominant} stick to control the task when the cursor "
                "is red."
            ),
            "wrong_hand_nd": (
                "Wrong hand!\n"
                f"Please use the {nondominant} stick to control the task when the "
                "cursor is blue."
            ),
            "continue": "Press any button to continue.",
        }
        self.errs = {}
        for key, txt in err_txt.items():
            self.errs[key] = message(txt, blit_txt=False, align="center")

        # Insert practice block
        self.insert_practice_block(1, trial_counts=P.practice_trials)

        # Run a visual demo explaining the task
        self.task_demo()


    def block(self):
        # Hide mouse cursor if not already hidden
        hide_cursor()

        # Define block messages
        dominant = "left" if self.handedness == "l" else "right"
        nondominant = "right" if self.handedness == "l" else "left"
        next_msg = "Press any button to start."
        block_msgs = {
            "PP": (
                "For this next set of trials, please respond to targets physically by\n"
                f"using the gamepad's {dominant} stick to move the cursor over them."
            ),
            "MI": (
                "For this next set of trials, please respond to targets using *motor "
                "imagery*,\nimagining what it would feel like to move the cursor over "
                "each target\n(without actually moving), then physically pressing the "
                f"{nondominant} trigger when finished.\n\nPlease keep your thumb "
                f"resting on the {dominant} stick."
            ),
            "CC": (
                "For this next set of trials, please respond to targets by simply "
                f"pressing\nthe {nondominant} trigger as quickly as possible, without "
                "moving the cursor."
            ),
            "test": (
                "The colour of the cursor will change randomly between trials, so be "
                "ready to\nrespond with either stick. Press any button when you are "
                "ready to begin!"
            ),
        }

        # Handle different phases of the experiment
        block_sequence = ["practice", "training", "test"]
        self.phase = block_sequence[P.block_number - 1]
        if self.phase == "practice":
            self.joystick_map = P.training_mapping
            self.trial_type = "PP"
            block_msg = "This is a practice block.\n\n" + block_msgs["PP"]
            block_msg = block_msg.replace("next", "first")
        elif self.phase == "training":
            self.joystick_map = P.training_mapping
            self.trial_type = P.condition
            block_msg = block_msgs[self.trial_type]
            if self.trial_type == "PP":
                block_msg = block_msg.replace("please", "please continue to")
        elif self.phase == "test":
            self.joystick_map = P.test_mapping
            self.trial_type = "PP"
            block_msg = block_msgs["test"]
            self.test_phase_instructions()

        # Generate sequence of hands to use for each trial
        self.dominant_hand = []
        if self.phase == "test":
            # Ensure there are 2 trials w/ each hand in every group of 4 trials
            subseq = [True, True, False, False]
            while len(self.dominant_hand) < P.trials_per_block:
                shuffle(subseq)
                self.dominant_hand += subseq
        else:
            self.dominant_hand = [True] * P.trials_per_block

        # Show block start message
        msg = message(block_msg, blit_txt=False, align="center")
        msg2 = message("Press any button to start.", blit_txt=False)
        self.show_feedback(msg, duration=2.0, location=self.msg_loc)
        fill()
        blit(msg, 5, self.msg_loc)
        blit(msg2, 5, self.lower_middle)
        flip()
        wait_for_input(self.gamepad)


    def trial_prep(self):

        # Generate trial factors
        self.target_angle = randrange(0, 360, 1)
        self.target_dist = randrange(self.target_dist_min, self.target_dist_max)
        self.target_loc = vector_to_pos(P.screen_c, self.target_dist, self.target_angle)
        self.target_onset = randrange(1000, 3000, 100)

        # Determine hand to use for trial
        self.dominant = self.dominant_hand[P.trial_number - 1]
        self.left_hand = (self.handedness == "l") == self.dominant

        # Add timecourse of events to EventManager
        self.evm.add_event('target_on', onset=self.target_onset)
        self.evm.add_event('timeout', onset=15000, after='target_on')

        # Set mouse to screen centre & ensure mouse pointer hidden
        mouse_pos(position=P.screen_c)
        hide_cursor()


    def trial(self):

        # Initialize trial response data
        movement_rt = None
        contact_rt = None
        response_rt = None
        initial_angle = None
        axis_data = []
        last_x, last_y = (-1, -1)

        # Get joystick mapping for the trial
        mod_x, mod_y = P.input_mappings[self.joystick_map]

        # Initialize trial stimuli
        cursor = self.cursor if self.dominant else self.cursor_nd
        fill(MIDGREY)
        blit(self.fixation, 5, P.screen_c)
        blit(cursor, 5, P.screen_c)
        flip()

        target_on = None
        first_loop = True
        over_target = False
        while self.evm.before('timeout'):
            q = pump(True)
            ui_request(queue=q)

            # Get latest joystick/trigger data from gamepad
            if self.gamepad:
                self.gamepad.update()

            # Filter, standardize, and possibly invert the axis & trigger data
            lt, rt = self.get_triggers()
            jx, jy = self.get_stick_position(self.left_hand)
            input_time = precise_time()
            cursor_pos = (
                P.screen_c[0] + int(jx * self.target_dist_max * mod_x),
                P.screen_c[1] + int(jy * self.target_dist_max * mod_y)
            )

            # Handle input based on trial type and trials phase
            triggers_released = lt < 0.2 and rt < 0.2
            cursor_movement = linear_dist(cursor_pos, P.screen_c)
            if target_on:
                # As soon as cursor moves after target onset, log movement RT
                if not movement_rt and cursor_movement > 0:
                    movement_rt = input_time - target_on
                # Once cursor has moved slightly away from origin, log initial angle
                if not initial_angle and px_to_deg(cursor_movement) > 0.1:
                    # Wait at least 50 ms after first movement before calculating angle
                    # (otherwise we get lots of 270s due to no y-axis change)
                    if input_time - (target_on + movement_rt) > 0.05:
                        initial_angle = vector_angle(P.screen_c, cursor_pos)

            # Check other joystick for movement if in test block
            other_stick_movement = 0.0
            if self.phase == "test":
                jx2, jy2 = self.get_stick_position(not self.left_hand)
                dist_raw = linear_dist((jx2, jy2), (0, 0))
                other_stick_movement = dist_raw * self.target_dist_max

            # Detect/handle different types of trial error
            err = "NA"
            if cursor_movement > self.cursor_size:
                if self.trial_type == "MI":
                    err = "stick_mi"
                elif self.trial_type == "CC":
                    err = "stick_cc"
                elif self.trial_type == "PP" and not target_on:
                    err = "too_soon"
            elif other_stick_movement > self.cursor_size:
                err = "wrong_hand" if self.dominant else "wrong_hand_nd"
            if first_loop:
                first_loop = False
                if not triggers_released:
                    err = "start_triggers"
            elif not target_on:
                if not triggers_released:
                    err = "too_soon"

            # If the participant did something wrong, show them a feedback message
            if err != "NA":
                self.show_feedback(self.errs[err], duration=2.0)
                fill()
                blit(self.errs[err], 5, P.screen_c)
                blit(self.errs['continue'], 5, self.lower_middle)
                flip()
                wait_for_input(self.gamepad)
                # If error happens early in the trial, recycle
                raise TrialException("Recycling trial!")

            # Log continuous cursor x/y data for each frame
            if target_on and cursor_movement and self.gamepad:
                # Only log samples where position actually changes (to save space)
                any_change = (cursor_pos[0] != last_x) or (cursor_pos[1] != last_y)
                if any_change:
                    axis_sample = (
                        int((input_time - target_on) * 1000), # timestamp
                        cursor_pos[0], # joystick x
                        cursor_pos[1], # joystick y
                    )
                    axis_data.append(axis_sample)
                last_x = cursor_pos[0]
                last_y = cursor_pos[1]
            
            # Actually draw stimuli to the screen
            fill()
            blit(self.fixation, 5, P.screen_c)
            if self.evm.after('target_on'):
                blit(self.target, 5, self.target_loc)
            blit(cursor, 5, cursor_pos)
            if P.development_mode and P.show_gamepad_debug:
                self.show_gamepad_debug()
            flip()

            # Get timestamp for when target drawn to the screen
            if not target_on and self.evm.after('target_on'):
                target_on = precise_time()
                
            # Check if the cursor is currently over the target
            dist_to_target = linear_dist(cursor_pos, self.target_loc)
            if dist_to_target < (self.cursor_size / 2):
                # Get timestamp for when cursor first touches target
                if not contact_rt:
                    contact_rt = precise_time() - target_on
                # To prevent participants from holding triggers down while moving the
                # stick (making the task much easier), the experiment only counts the
                # cursor as being over the target if both triggers are released while
                # over it.
                triggers_released = lt < 0.2 and rt < 0.2
                if not over_target and triggers_released:
                    over_target = True
            else:
                over_target = False

            # If either trigger pressed when it is possible to respond, end the trial
            can_respond = over_target or self.trial_type != "PP"
            if can_respond and (lt > 0.5 or rt > 0.5):
                response_rt = precise_time() - target_on
                break

        # Show RT feedback for 1 second (may remove this)
        if response_rt:
            rt_sec = "{:.3f}".format(response_rt)
            feedback = message(rt_sec, blit_txt=False)
            self.show_feedback(feedback, duration=1.5)
        elif err == "NA":
            feedback = self.errs['too_slow']
            self.show_feedback(feedback, duration=2.5)

        # Write raw axis data to database
        if err == "NA":
            rows = []
            for timestamp, stick_x, stick_y in axis_data:
                rows.append({
                    'participant_id': P.participant_id,
                    'block_num': P.block_number,
                    'trial_num': P.trial_number,
                    'time': timestamp,
                    'stick_x': stick_x,
                    'stick_y': stick_y,
                })
            self.db.insert(rows, table='gamepad')

        return {
            "block_num": P.block_number,
            "trial_num": P.trial_number,
            "trial_type": self.trial_type,
            "mapping": self.joystick_map,
            "dominant": self.dominant,
            "target_onset": self.target_onset if target_on else "NA",
            "target_dist": px_to_deg(self.target_dist),
            "target_angle": self.target_angle,
            "movement_rt": "NA" if movement_rt is None else movement_rt * 1000,
            "contact_rt": "NA" if contact_rt is None else contact_rt * 1000,
            "response_rt": "NA" if response_rt is None else response_rt * 1000,
            "initial_angle": "NA" if initial_angle is None else initial_angle,
            "err": err,
            "target_x": self.target_loc[0],
            "target_y": self.target_loc[1],
        }


    def trial_clean_up(self):
        pass


    def clean_up(self):
        
        end_txt = (
            "You're all done, thanks for participating!\nPress any button to exit."
        )
        end_msg = message(end_txt, blit_txt=False, align='center')
        fill()
        blit(end_msg, 5, P.screen_c)
        flip()
        wait_for_input(self.gamepad)

        if self.gamepad:
            self.gamepad.close()


    def show_demo_text(self, msgs, stim_set, duration=1.0, wait=True, msg_y=None):
        msg_x = int(P.screen_x / 2)
        msg_y = int(P.screen_y * 0.25) if msg_y is None else msg_y
        half_space = deg_to_px(0.5)

        fill()
        if not isinstance(msgs, list):
            msgs = [msgs]
        for msg in msgs:
            txt = message(msg, blit_txt=False, align="center")
            blit(txt, 8, (msg_x, msg_y))
            msg_y += txt.height + half_space
    
        for stim, locs in stim_set:
            if not isinstance(locs, list):
                locs = [locs]
            for loc in locs:
                blit(stim, 5, loc)
        flip()
        smart_sleep(duration * 1000)
        if wait:
            wait_for_input(self.gamepad)


    def task_demo(self):
        # Initialize task stimuli for the demo
        target_dist = (2 * self.target_dist_min + self.target_dist_max) / 3
        target_loc = vector_to_pos(P.screen_c, target_dist, 250)
        feedback = message("{:.3f}".format(2.841), blit_txt=False)
        base_layout = [
            (self.fixation, P.screen_c),
            (self.cursor, P.screen_c),
        ]
        dominant = "left" if self.handedness == "l" else "right"
        nondominant = "right" if self.handedness == "l" else "left"
        
        # Actually run through demo
        self.show_demo_text(
            "Welcome to the experiment! This tutorial will help explain the task.",
            [(self.fixation, P.screen_c), (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            ("On each trial of the task, a small white target will appear at a random "
             "distance\nfrom the fixation cross at the middle of the screen."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            ("Your job will be to quickly move the red cursor over top of the target "
             f"when it appears,\nusing the {dominant} stick on the gamepad."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             (self.cursor, (target_loc[0] + 4, target_loc[1] + 6))]
        )
        self.show_demo_text(
            ("Once you have moved the cursor over the target, please squeeze the "
             f"{nondominant} trigger on the \nback of the gamepad to end the trial. "
             "You will be shown your reaction time."),
            [(feedback, P.screen_c)]
        )
        target_dist = (self.target_dist_min + self.target_dist_max) / 2
        target_loc = vector_to_pos(P.screen_c, target_dist, 165)
        if P.condition == "MI":
            feedback = message("{:.3f}".format(3.347), blit_txt=False)
            self.show_demo_text(
                ("In some parts of the study, you will be asked to perform this task "
                "using motor imagery,\ni.e. imagine what it would *look and feel like* "
                "to move the cursor over the target."),
                [(self.fixation, P.screen_c), (self.target, target_loc),
                (self.cursor, P.screen_c)]
            )
            self.show_demo_text(
                ("When the target appears on an imagery trial, try to mentally "
                 "simulate performing\nthe thumb movement required to move the cursor "
                 "over the target (without actually moving)."),
                [(self.fixation, P.screen_c), (self.target, target_loc),
                 (self.cursor, P.screen_c)]
            )
            self.show_demo_text(
                ("Once you have imagined the movement and are over the target (in your "
                 f"mind's eye),\nplease physically squeeze the {nondominant} trigger "
                  "to end the trial."),
                [(feedback, P.screen_c)]
            )
        if P.condition == "CC":
            self.show_demo_text(
                ("In some parts of the study, instead of moving the cursor to the "
                 f"target, you will be\nasked to simply squeeze the {nondominant} "
                 "trigger as soon as the target appears."),
                [(self.fixation, P.screen_c), (self.target, target_loc),
                (self.cursor, P.screen_c)]
            )
            self.show_demo_text(
                ("As usual, pressing the trigger will end the trial and display your "
                 "reaction time.\nPlease try to respond as quickly as possible."),
                [(feedback, P.screen_c)]
            )


    def test_phase_instructions(self):
        # Initialize task stimuli for the demo
        target_dist = (2 * self.target_dist_min + self.target_dist_max) / 3
        target_loc = vector_to_pos(P.screen_c, target_dist, 250)
        dominant = "left" if self.handedness == "l" else "right"
        nondominant = "right" if self.handedness == "l" else "left"

        self.show_demo_text(
            ("For this next set of trials, please respond to targets physically using "
             "the\njoysticks on the gamepad. During this block, the cursor will "
             "alternate\nbetween red and blue."),
            [(self.fixation, P.screen_c), (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            (f"When the cursor is *red*, please use the {dominant} stick to move the "
             f"cursor to\nthe target and squeeze the {nondominant} trigger to end "
             "the trial (same as before)."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            (f"When the cursor is *blue*, please use the *{nondominant}* stick to "
             f"control the cursor\n(with your other hand) and squeeze the *{dominant}* "
             "trigger to end the trial."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             (self.cursor_nd, P.screen_c)]
        )


    def show_gamepad_debug(self):
        if not self.gamepad:
            return

        # Get latest axis info
        rs_x, rs_y = self.gamepad.right_stick()
        ls_x, ls_y = self.gamepad.left_stick()
        lt = self.gamepad.left_trigger()
        rt = self.gamepad.right_trigger()
        dpad_x, dpad_y = self.gamepad.dpad()

        # Blit axis state info to the bottom-right of the screen
        info_txt = "\n".join([
            "Left Stick: ({0}, {1})",
            "Right Stick: ({2}, {3})",
            "Left Trigger: {4}",
            "Right Trigger: {5}",
            "D-Pad: ({6}, {7})",
        ]).format(ls_x, ls_y, rs_x, rs_y, lt, rt, dpad_x, dpad_y)
        pad_info = message(info_txt, style='debug', blit_txt=False)
        blit(pad_info, 1, (0, P.screen_y))


    def show_feedback(self, msg, duration=1.0, location=None):
        feedback_time = CountDown(duration)
        if not location:
            location = P.screen_c
        while feedback_time.counting():
            ui_request()
            if self.gamepad:
                self.gamepad.update()
            fill()
            blit(msg, 5, location)
            flip()
        
    
    def get_stick_position(self, left=False):
        if self.gamepad:
            if left:
                raw_x, raw_y = self.gamepad.left_stick()
            else:
                raw_x, raw_y = self.gamepad.right_stick()
        else:
            # If no gamepad, approximate joystick with mouse movement
            mouse_x, mouse_y = mouse_pos()
            scale_factor = AXIS_MAX / self.target_dist_max
            raw_x = int((mouse_x - P.screen_c[0]) * scale_factor)
            raw_y = int((mouse_y - P.screen_c[1]) * scale_factor)

        return joystick_scaled(raw_x, raw_y)

    
    def get_triggers(self):
        if self.gamepad:
            raw_lt = self.gamepad.left_trigger()
            raw_rt = self.gamepad.right_trigger()
        else:
            # If no gamepad, emulate trigger press with mouse click
            raw_lt, raw_rt = (0, 0)
            mouse_x, mouse_y = c_int(0), c_int(0)
            if sdl2.SDL_GetMouseState(byref(mouse_x), byref(mouse_y)) != 0:
                # Ignore mouse button down for first 100 ms to ignore start-trial click
                if self.evm.trial_time_ms > 100:
                    raw_lt, raw_rt = (32767, 32767)

        return (raw_lt / TRIGGER_MAX, raw_rt / TRIGGER_MAX)



def joystick_scaled(x, y, deadzone = 0.2):

    # Check whether the current stick x/y exceeds the specified deadzone
    amplitude = min(1.0, sqrt(x ** 2 + y ** 2) / AXIS_MAX)
    if amplitude < deadzone:
        return (0, 0)

    # Smooth/standardize output coordinates to be on a circle, by capping
    # maximum amplitude at AXIS_MAX and converting stick angle/amplitude
    # to coordinates.
    angle = angle_between((0, 0), (x, y))
    amp_new = (amplitude - deadzone) / (1.0 - deadzone)
    xs, ys = point_pos((0, 0), amp_new, angle, return_int=False)

    return (xs, ys)

    
def wait_for_input(gamepad=None):
    valid_input = [
        sdl2.SDL_KEYDOWN,
        sdl2.SDL_MOUSEBUTTONDOWN,
        sdl2.SDL_CONTROLLERBUTTONDOWN,
    ]
    flush()
    user_input = False
    while not user_input:
        if gamepad:
            gamepad.update()
        q = pump(True)
        ui_request(queue=q)
        for event in q:
            if event.type in valid_input:
                user_input = True
                break


def vector_angle(p1, p2):
    # Gets the angle of a vector relative to directly upwards
    return angle_between(p1, p2, rotation=-90, clockwise=True)


def vector_to_pos(origin, amplitude, angle, return_int=True):
    # Gets the (x,y) coords of a vector's endpoint given its origin/angle/length
    # (0 degrees is directly up, 90 deg. is directly right, etc.)
    return point_pos(origin, amplitude, angle, rotation=-90, clockwise=True)
