from klibs import P
from klibs.KLTime import Stopwatch
from klibs.KLEventQueue import flush, pump
from klibs.KLUserInterface import (
    key_pressed, ui_request, show_cursor, hide_cursor, smart_sleep, any_key,
)
from klibs.KLUtilities import deg_to_px
from klibs.KLGraphics import fill, blit, flip
from klibs.KLCommunication import message

from InterfaceExtras import Button, LikertType, ThoughtProbe, Aesthetics


# KVIQ-10 elements
# 1. Forward shoulder flexion
#    - Starting with arm at side, lift arm straight up, keeping elbow straight
# 2. Thumb-fingers opposition
#    - Tap thumb to each finger on same hand, starting w/ pinkie & going inward
# 3. Forward trunk flexion
#    - Bend forwards
# 4. Hip abduction
#    - Move leg away from body (move leg outward if sitting)
# 5. Foot tapping
#    - Just tapping foot up and down in place, heel on floor

physical = (
    "First, we'll perform the movement physically.\nWhen you press the space bar "
    "to start, please "
)

visual = (
    "Next, we'll imagine the same movement visually, from a 3rd-person "
    "perspective.\nWhen you press the space bar to start, please close your eyes and "
    "imagine watching someone else "
)
kinaesthetic = (
    "Finally, we'll imagine the movement kinaesthetically, from a 1st-person "
    "perspective.\nWhen you press the space bar to start, please close your eyes and "
    "imagine how would look and feel to "
)

#movement_end_msg = ("When you are finished, please press the space bar again to "
#    "indicate that you are done.")

kviq_movements = {
    'Forward Shoulder Flexion': {
        '3rd_sub': {'raise ': 'raising ', 'lower': 'lowering', 'your': 'their'},
        'start_pos': "with your left arm flat against your side.",
        'desc': (
            "raise your left arm forwards with a straight elbow until it is fully "
            "raised, then lower it to its original position."
        ),
    },
    'Thumb-Fingers Opposition': {
        '3rd_sub': {'tap': 'tapping', 'your': 'their'},
        'start_pos': "with your left hand raised and your palm facing upwards.",
        'desc': (
            "tap your thumb to each finger on your left hand, starting with the pinkie "
            "and moving inward."
        ),
    },
    'Forward Trunk Flexion': {
        '3rd_sub': {'bend': 'bending', 'return': 'returning', 'your': 'their'},
        'start_pos': "upright in a comfortable position.",
        'desc': (
            "bend forwards in your seat to look at the floor, then return to your "
            "original sitting position."
        ),
    },
    'Hip Abduction': {
        '3rd_sub': {'move': 'moving', 'your': 'their'},
        'start_pos': "with your feet and knees together.",
        'desc': (
            "move your left leg away from your other leg and then return to your "
            "original position, keeping your knees bent."
        ),
    },
    'Foot Tapping': {
        '3rd_sub': {'tap': 'tapping', 'your': 'their'},
        'start_pos': "upright in a comfortable position.",
        'desc': (
            "tap your left foot 8 times on the floor, keeping your heel in place."
        ),
    },
}

start_pos_prefix = "The starting position for this movement is to be sitting "
movement_prefix = "To perform this movement, please "
wait_msg = (
    "Please wait for a researcher to demonstrate the movement before you continue."
)

visual_ratings = {
    '5': "5 - Image as clear as seeing",
    '4': "4 - Clear image",
    '3': "3 - Moderately clear image",
    '2': "2 - Blurry image",
    '1': "1 - No image",
}

kinaesthetic_ratings = {
    '5': "5 - As intense as executing the action",
    '4': "4 - Intense",
    '3': "3 - Moderately intense",
    '2': "2 - Mildly intense",
    '1': "1 - No sensation",
}


def demo_msg(msgs, wait=1.0, resp=True, msg_y=None):
    msg_x = int(P.screen_x / 2)
    msg_y = int(P.screen_y * 0.4) if msg_y is None else msg_y
    half_space = deg_to_px(0.5)
    wrap = int(P.screen_x * 0.7)

    fill()
    if not isinstance(msgs, list):
        msg_y = int(P.screen_y * 0.15)
        msgs = [msgs]
    for msg in msgs:
        txt = message(msg, blit_txt=False, align="center", wrap_width=wrap)
        blit(txt, 8, (msg_x, msg_y))
        msg_y += txt.height + half_space
    flip()

    if wait:
        smart_sleep(wait * 1000)
    if resp:
        any_key()



class KVIQ(object):

    def __init__(self, left_handed=False):
        self.left_handed = left_handed


    def run(self):
        # Runs the full KVIQ and returns responses in a dict
        responses = {}
        for name, movement in kviq_movements.items():
            responses[name] = self._collect_movement(movement)
        return responses


    def _collect_movement(self, info):
        # Generate 1st and 3rd-person movement descriptions
        left_h = self.left_handed
        desc_1st = info['desc'].replace('left', 'right') if left_h else info['desc']
        desc_3rd = desc_1st
        for word, replacement in info['3rd_sub'].items():
            desc_3rd = desc_3rd.replace(word, replacement)

        # Explain the movement and starting position
        if left_h:
            info['start_pos'] = info['start_pos'].replace('left', 'right')
        info = [
            start_pos_prefix + info['start_pos'],
            movement_prefix + desc_1st,
            " ",
            wait_msg,
        ]
        demo_msg(info)

        # Perform movement physically first
        dat = {}
        phys_instructions = (physical + desc_1st).split("\n")
        dat['physical_time'] = self._wait_for_movement(phys_instructions)

        # Next, visualize in 3rd person
        visual_instructions = (visual + desc_3rd).split("\n")
        dat['visual_time'] = self._wait_for_movement(visual_instructions)
        dat['vividness'] = self._collect_rating()

        # Finally, visualize in 1st person
        kin_instructions = (kinaesthetic + desc_1st).split("\n")
        dat['kinaesthetic_time'] = self._wait_for_movement(kin_instructions)
        dat['intensity'] = self._collect_rating(kinaesthetic=True)

        return dat
        

    def _wait_for_movement(self, instructions):
        # Present the initial instructions and wait for input
        spacebar_txt = [" ", "Press the space bar to begin."]
        demo_msg(instructions + spacebar_txt, wait=False)

        # Once started, remove 'press space to start' prompt and wait for second
        # space bar press to end.
        timer = Stopwatch(start=True)
        demo_msg(instructions, wait=False)
        timer.pause()

        # On second press, return movement duration
        return timer.elapsed()


    def _collect_rating(self, kinaesthetic=False):
        # Generate the prompt and rating choices based on the type of imagery
        prompt_txt = "Using the scale below, how {0} was the imagined movement?"
        if kinaesthetic:
            prompt_adj = "intense"
            choices = kinaesthetic_ratings
        else:
            prompt_adj = "clear"
            choices = visual_ratings
        prompt = message(prompt_txt.format(prompt_adj), blit_txt=False)

        # Create the rating prompt for the current imagery type
        scale_loc = (P.screen_c[0], int(P.screen_y * 0.3))
        scale = ThoughtProbe(
            choices, prompt, scale_loc, order = ['5', '4', '3', '2', '1']
        )

        # Collect and return the rating
        rating = scale.collect()
        return int(rating.value)
