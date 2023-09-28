import re

from klibs import P
from klibs.KLTime import Stopwatch
from klibs.KLEventQueue import flush, pump
from klibs.KLUserInterface import (
    key_pressed, ui_request, show_cursor, hide_cursor, smart_sleep, mouse_clicked,
)
from klibs.KLUtilities import deg_to_px
from klibs.KLGraphics import fill, blit, flip, NumpySurface
from klibs.KLCommunication import message

from InterfaceExtras import RatingScale


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

imagery_desc = [
    "Thank you for participating in this study!\n",
    ("At some points during the experiment you will be asked to perform 'motor "
     "imagery', which is defined as the mental rehearsal of movement. Specifically, "
     "motor imagery involves simulating in your mind what it would *feel like* to "
     "perform a given movement (without actually performing it)."),
    ("For example, if you were to perform motor imagery of clapping your hands "
     "together, you might imagine the feeling of opening your palms, the motion of "
     "your arms, and the feeling of your hands coming into contact. You might also "
     "imagine what it would look or sound like to perform the action.")
]

intro_1 = [
    ("Before you start the main task, we are going to do a quick assessment of the "
     "clarity\n"
     "and intensity with which you can perform motor imagery. This will involve "
     "performing\n"
     "and then imagining five different movements."),
]
intro_2 = [
    "You will perform each movement three times: once physically, and twice mentally.\n",
    ("First, after the movement has been explained to you, you will perform\n"
     "it physically to familiarize yourself with how it looks and feels."),
    ("Second, you will be asked to imagine what it would look like to watch\n"
     "*someone else* perform that movement (third-person imagery)."),
    ("Finally, you will be asked to imagine what it would feel like to perform\n"
     "the movement *yourself* (first-person imagery)."),
]
intro_3 = [
    ("Some of the movements will be done with the dominant side of your body,\n"
     "others will be done with the non-dominant side."),
    ("To record how long each movement takes, please press the space bar when\n"
     "you start the movement and then press it again when you have finished."),
    ("If a movement requires the use of an arm or hand, please use the\n"
     "*opposite* hand to press the space bar."),
]
intro_4 = [
    ("Each time you imagine watching someone else perform a movement, you will be "
     "asked\n"
     "to rate the clarity of your mental image on a scale from 1 to 5."),
    "Press any key to see an example of this scale.",
]
intro_5 = [
    ("Similarly, each time you imagine performing the movement yourself, you will be "
     "asked\n"
     "to rate the intensity of the imagined sensations on a scale from 1 to 5."),
    "Press any key to see an example of this scale.",
]
intro_6 = [
    ("You're almost ready to start! If you have any questions about the task, please "
     "raise your hand now.\n"
     "Otherwise, press any key to read the description of the first movement."),
]

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


kviq_movements = {
    'Forward Shoulder Flexion': {
        '3rd_sub': {'raise ': 'raising ', 'lower': 'lowering', 'your': 'their'},
        'start_pos': "with your left arm\nflat against your side.",
        'desc': (
            "raise your left arm forwards with a straight elbow until it is fully "
            "raised, then lower it to its original position."
        ),
    },
    'Thumb-Fingers Opposition': {
        '3rd_sub': {'tap': 'tapping', 'your': 'their'},
        'start_pos': "with your right hand\nraised and your palm facing upwards.",
        'desc': (
            "tap your thumb to each finger on your right hand, starting with the "
            "pinkie and moving inward."
        ),
    },
    'Forward Trunk Flexion': {
        '3rd_sub': {'bend': 'bending', 'return': 'returning', 'your': 'their'},
        'start_pos': "upright in\na comfortable position.",
        'desc': (
            "bend forwards in your seat to look at the floor, then return to your "
            "original sitting position."
        ),
    },
    'Hip Abduction': {
        '3rd_sub': {'move': 'moving', 'your': 'their'},
        'start_pos': "with your\nfeet and knees together.",
        'desc': (
            "move your right leg away from your other leg and then return to your "
            "original position, keeping your knees bent."
        ),
    },
    'Foot Tapping': {
        '3rd_sub': {'tap': 'tapping', 'your': 'their'},
        'start_pos': "upright in\na comfortable position.",
        'desc': (
            "tap your left foot 5 times on the floor, keeping your heel in place."
        ),
    },
}

start_pos_prefix = "The starting position for this movement is to be sitting "
movement_prefix = "To perform this movement, please "
wait_msg = "Please wait for a researcher to demonstrate the movement."

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

def render_text(msgs, spacing=None, align="center", width=None):
    # Initialize defaults and inputs
    if not isinstance(msgs, list):
        msgs = [msgs]
    if not spacing:
        spacing = deg_to_px(0.5) # change to default text height in pixels?
    if not width:
        width = int(P.screen_x * 0.8)

    # Render all chunks of text and determine the total height
    total_height = 0
    rendered = []
    for msg in msgs:
        # If we're in between paragraphs, insert padding
        if len(rendered) > 0:
            total_height += spacing
        # Render the message and add its height to the total
        chunk = message(msg, blit_txt=False, align=align, wrap_width=width)
        total_height += chunk.height
        rendered.append(chunk)

    # Combine all rendered chunks into a single surface texture
    surf = NumpySurface(width=width, height=total_height)
    y_pos = 0
    x_pos = int(width / 2) if align == "center" else 0
    blit_reg = 8 if align == "center" else 7
    for msg in rendered:
        # If not on first message, add between-chunk padding
        if y_pos > 0:
            y_pos += spacing
        # Render the text to the surface
        surf.blit(msg, blit_reg, (x_pos, y_pos), blend=False)
        y_pos += msg.height

    return surf


def demo_msg(msgs, extras=None, wait=0.1, resp=True, spacing=None, width=None):

    if not extras:
        extras = []
    msg_surf = render_text(msgs, spacing=spacing, width=width)

    fill()
    blit(msg_surf, 5, P.screen_c)
    for e in extras:
        blit(e['img'], e['reg'], e['loc'])
    flip()

    if wait:
        smart_sleep(wait * 1000)
    flush()
    while resp:
        q = pump(True)
        if key_pressed('space', queue=q) or mouse_clicked(queue=q):
            break


def swap_laterality(txt):
    # Swaps left/right in a given string of text
    txt = re.sub(r"(\s)right([\s\.,])", "\1left\2", txt)
    txt = re.sub(r"(\s)left([\s\.,])", "\1right\2", txt)
    return txt



class KVIQ(object):

    def __init__(self, left_handed=False):
        self.left_handed = left_handed
        self.extras = [] # Extra stimuli for demo_msg


    def run(self):
        self._instructions()
        # Runs the full KVIQ and returns responses in a dict
        responses = {}
        for name, movement in kviq_movements.items():
            self._update_title(name)
            responses[name] = self._collect_movement(movement)
        return responses


    def _update_title(self, movement):
        loc = (P.screen_c[0], int(P.screen_y * 0.15))
        title = message(movement, style="title", blit_txt=False)
        self.extras = [{'img': title, 'reg': 8, 'loc': loc}] 


    def _instructions(self):
        demo_msg(imagery_desc)
        demo_msg(intro_1)
        demo_msg(intro_2)
        demo_msg(intro_3)

        demo_msg(intro_4)
        self._collect_rating(kinaesthetic=False, demo=True)

        demo_msg(intro_5)
        self._collect_rating(kinaesthetic=True, demo=True)

        demo_msg(intro_6)


    def _collect_movement(self, info):
        # Generate 1st and 3rd-person movement descriptions
        left_h = self.left_handed
        desc_1st = swap_laterality(info['desc']) if left_h else info['desc']
        desc_3rd = desc_1st
        for word, replacement in info['3rd_sub'].items():
            desc_3rd = desc_3rd.replace(word, replacement)

        # Explain the movement and starting position
        if left_h:
            info['start_pos'] = swap_laterality(info['start_pos'])
        info = [
            start_pos_prefix + info['start_pos'],
            movement_prefix + desc_1st + "\n",
            wait_msg,
        ]
        demo_msg(info, self.extras, width=int(P.screen_x * 0.65))

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
        instructions[-1] = instructions[-1] + "\n"
        instructions += ["Press [space] to begin."]
        demo_msg(instructions, self.extras, wait=False, width=int(P.screen_x * 0.65))

        # Once started, remove 'press space to start' prompt and wait for second
        # space bar press to end.
        timer = Stopwatch(start=True)
        demo_msg("Press [space] when finished.", wait=0.5)
        timer.pause()

        # On second press, return movement duration
        return timer.elapsed()


    def _collect_rating(self, kinaesthetic=False, demo=False):
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
        scale = RatingScale(
            choices, prompt, scale_loc, order = ['5', '4', '3', '2', '1']
        )

        # Collect and return the rating
        response = 0
        if demo:
            show_cursor()
            while True:
                q = pump(True)
                if key_pressed(' ', queue=q) or mouse_clicked(queue=q):
                    break
                fill()
                scale._render()
                flip()
            hide_cursor()
        else:
            rating = scale.collect()
            response = rating.value
        return int(response)
