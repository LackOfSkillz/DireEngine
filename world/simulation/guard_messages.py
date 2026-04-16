import random


ENTER_MESSAGES = [
    "The guard glances up as you enter.",
    "A guard briefly sizes you up as you arrive.",
    "The guard's eyes track your approach.",
    "A guard shifts slightly, noting your presence.",
    "The guard gives you a measured look.",
    "A guard watches you enter, expression unreadable.",
]


EXIT_MESSAGES = [
    "The guard watches you leave.",
    "A guard's gaze follows you as you depart.",
    "The guard glances after you briefly.",
    "A guard notes your exit with a faint nod.",
    "The guard's attention lingers as you go.",
    "A guard tracks your departure before returning to watch.",
]


OBSERVE_MESSAGES = [
    "The guard scans the street with practiced focus.",
    "A guard adjusts their stance, remaining alert.",
    "The guard rests a hand near their weapon, watching.",
    "A guard surveys the area with a steady gaze.",
    "The guard shifts weight slightly, ever watchful.",
    "A guard stands at ease, eyes moving over the street.",
]


def get_enter_message():
    return random.choice(ENTER_MESSAGES)


def get_exit_message():
    return random.choice(EXIT_MESSAGES)


def get_observe_message():
    return random.choice(OBSERVE_MESSAGES)