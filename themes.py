# Each theme is (angle, visual_direction).
# angle  = the emotional / human story that drives the post
# visual  = specific scene to render
THEMES = [
    (
        "Moving into your first place — bare walls, big dreams, zero budget for a contractor",
        "A fresh empty apartment, warm afternoon light, one or two items just hung on a clean wall",
    ),
    (
        "Your landlord thinks you haven't touched the walls. You have.",
        "A beautifully decorated rental — gallery wall, hooks, mounted shelves — pristine walls, zero nail holes",
    ),
    (
        "That corner you walked past every day and cringed at. Fixed.",
        "A previously ignored corner now beautifully organised — coat hook, small shelf, or framed art in place",
    ),
    (
        "The kind of bathroom that makes you feel like you're at a boutique hotel",
        "A minimal spa-like bathroom, white tile, towels hanging from a sleek hook, warm morning light",
    ),
    (
        "Sunday morning in the home you've always wanted",
        "A sun-filled living room corner, beautifully styled, calm and aspirational",
    ),
    (
        "Your entryway sets the mood for your whole day. Make it count.",
        "A modern apartment entryway — coat, bag, and keys each in their perfect place on the wall",
    ),
    (
        "When guests arrive and ask 'wait, how is that hanging there?'",
        "A beautifully mounted mirror or gallery wall with no visible nails, screws, or hardware",
    ),
    (
        "The before photo nobody wants to share. The after photo everyone saves.",
        "Split composition — LEFT: bare messy wall; RIGHT: the same space perfectly organised and styled",
    ),
    (
        "A gallery wall that took 20 minutes and will cost you nothing to move",
        "4-6 different frames arranged beautifully on a warm-toned wall, no nail holes visible",
    ),
    (
        "Your rug keeps curling. Your guests keep tripping. Not anymore.",
        "A beautifully flat rug lying perfectly smooth on hardwood floors, styled room in the background",
    ),
    (
        "Kitchen goals: everything within reach, nothing in the way",
        "A beautifully organised kitchen — utensils or spice jars mounted neatly on the wall or cabinet side",
    ),
    (
        "Plant mum / dad level unlocked: hanging garden, zero holes in the ceiling",
        "Lush trailing plants hanging at different heights near a window, hooks on the wall holding them",
    ),
    (
        "5 minutes. One strip. The whole room changed.",
        "A dramatic room transformation shown in a single aspirational styled shot",
    ),
    (
        "Decorating without commitment — because your taste evolves",
        "A person casually rearranging frames on a wall with ease, warm candid moment, real home setting",
    ),
    (
        "Heavy things. Clean walls. No compromise.",
        "A large heavy mirror or thick wooden frame mounted perfectly on a clean wall — no damage visible",
    ),
    (
        "The home that looks designed but cost nothing to change",
        "An editorial-quality styled room that could belong in a home magazine — clean, intentional, beautiful",
    ),
    (
        "What your morning routine looks like when your home actually works",
        "A calm morning scene — coat on a hook, keys hanging, bag in place — everything where it belongs",
    ),
    (
        "Renters deserve beautiful homes too",
        "A beautifully styled rental apartment — art on walls, hooks, organised spaces — looking like an owned home",
    ),
    (
        "The detail nobody notices but everyone feels",
        "An extreme close-up of something mounted perfectly — a frame edge flush to a wall, a rug corner flat",
    ),
    (
        "Organised is the new aesthetic",
        "A room scene where everything is perfectly in its place — minimal, intentional, deeply satisfying",
    ),
]


def get_scene_for_product(product: dict, angle: str, visual: str) -> str:
    """Ground the visual in what this specific product actually does."""
    folder = product["folder"]
    use_cases = ", ".join(product["use_cases"])

    if folder.startswith("KMHS"):
        what_it_does = (
            "magnetic strips that mount pictures, clocks, and objects to walls with no nails — "
            "objects appear to float cleanly on the wall"
        )
    elif folder.startswith("KSS") or folder.startswith("KST"):
        what_it_does = (
            "clear double-sided nano tape that mounts frames, secures rugs flat, and holds shelves — "
            "completely invisible once applied"
        )
    elif folder.startswith("KSH"):
        what_it_does = (
            "small adhesive wall hooks that hold towels, coats, bags, plants, and kitchen items — "
            "the hook backing presses flat against any wall surface with no drilling"
        )
    else:
        what_it_does = f"adhesive home organizer used for: {use_cases}"

    return (
        f"{visual}. "
        f"The scene shows the outcome of using {what_it_does}. "
        f"Relevant use cases: {use_cases}."
    )


def get_copy_lines(product: dict) -> list[str]:
    """Return punchy, product-type-specific Instagram copy lines."""
    folder = product["folder"]

    if folder.startswith("KMHS"):
        return [
            "Float it on the wall.\nNo nails. No kidding.",
            "Walls that work for you.\nZero holes required.",
            "Magnetic hold.\nClean finish.",
            "Heavy things. Clean walls.\nNo compromise.",
            "Mount it. Move it.\nRepeat.",
        ]
    if folder.startswith("KSS") or folder.startswith("KST"):
        return [
            "Invisible hold.\nVisible results.",
            "Flat floors. Happy home.\nZero trace.",
            "Peel. Press. Perfect.\nEvery time.",
            "Secure it. Style it.\nLeave no mark.",
            "The tape that disappears.\nThe results that don't.",
        ]
    if folder.startswith("KSH"):
        return [
            "Hang it. Love it.\nKeep your deposit.",
            "No screws.\nNo excuses.",
            "Your walls finally\nwork for you.",
            "Hook it up.\nNo tools needed.",
            "Everything in its place.\nZero damage.",
        ]
    return [
        "No nails. No limits.\nJust results.",
        "Your home. Your rules.\nZero holes.",
        "Stick it. Style it.\nLeave nothing behind.",
        "5 minutes.\nZero tools. This.",
        "Clean hold.\nEvery time.",
    ]
