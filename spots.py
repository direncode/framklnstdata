"""
Franklin Street Panopticon v1 - Location Database
==================================================
Curated high-visibility spots on/near Franklin Street for QR code and flyer placement.

Scores are 1-10 based on:
  - foot_traffic: volume of pedestrians (evening bias for trivia nights)
  - dwell_time: how long people linger (waiting, eating, browsing)
  - visibility: how easy it is to see a flyer/QR code posted here
  - student_density: proportion of foot traffic that's UNC students

Each spot includes lat/lon for mapping and a human-readable rationale.
"""

FRANKLIN_STREET_SPOTS = [
    {
        "id": 1,
        "name": "Bandidos Entrance (Home Base)",
        "lat": 35.9132,
        "lon": -79.0558,
        "address": "159 1/2 E Franklin St",
        "foot_traffic": 8,
        "dwell_time": 9,
        "visibility": 10,
        "student_density": 9,
        "best_times": ["5pm-7pm", "9pm-11pm"],
        "rationale": (
            "Your home venue. People entering/exiting will see QR codes on the door, "
            "window, and host stand. Maximum dwell time since they're already committed "
            "to being here."
        ),
        "placement_tip": (
            "Place a large QR code poster on the front window and a table tent "
            "on every table inside. Add one on the bathroom door."
        ),
    },
    {
        "id": 2,
        "name": "Top of the Hill (TOPO) Entrance",
        "lat": 35.9130,
        "lon": -79.0562,
        "address": "100 E Franklin St",
        "foot_traffic": 9,
        "dwell_time": 7,
        "visibility": 9,
        "student_density": 9,
        "best_times": ["7pm-12am"],
        "rationale": (
            "One of the busiest bar/restaurant entrances on Franklin. Heavy student "
            "foot traffic especially Thu-Sat evenings. People wait outside and check "
            "phones - perfect QR code moment."
        ),
        "placement_tip": (
            "Tape a flyer on the bulletin board near the entrance or ask staff if you "
            "can leave a stack of cards on the host stand."
        ),
    },
    {
        "id": 3,
        "name": "He's Not Here / Back Bar Alley",
        "lat": 35.9128,
        "lon": -79.0547,
        "address": "112 1/2 W Franklin St",
        "foot_traffic": 8,
        "dwell_time": 8,
        "visibility": 7,
        "student_density": 10,
        "best_times": ["8pm-1am"],
        "rationale": (
            "Iconic UNC bar. The alley approach funnels foot traffic past a narrow "
            "corridor - captive audience. Students waiting in line have nothing to do "
            "but look at their surroundings."
        ),
        "placement_tip": (
            "Post a flyer on the fence/wall along the alley approach. "
            "The line forms here on busy nights - people will scan out of boredom."
        ),
    },
    {
        "id": 4,
        "name": "Franklin St & Columbia St Intersection",
        "lat": 35.9131,
        "lon": -79.0540,
        "address": "Franklin St & Columbia St",
        "foot_traffic": 10,
        "dwell_time": 6,
        "visibility": 9,
        "student_density": 8,
        "best_times": ["11am-2pm", "5pm-8pm"],
        "rationale": (
            "Highest pedestrian volume intersection on Franklin. Students cross here "
            "going to/from campus. The crosswalk wait creates a natural pause where "
            "people look around."
        ),
        "placement_tip": (
            "Tape flyers to utility poles at eye level on all four corners. "
            "The NE corner (campus side) gets the most student traffic."
        ),
    },
    {
        "id": 5,
        "name": "Sutton's Drug Store / Alpine Bagel Area",
        "lat": 35.9134,
        "lon": -79.0551,
        "address": "159 E Franklin St",
        "foot_traffic": 7,
        "dwell_time": 8,
        "visibility": 8,
        "student_density": 9,
        "best_times": ["7am-11am", "11:30am-1:30pm"],
        "rationale": (
            "Morning and lunch rush hub. Students grabbing coffee and bagels pause "
            "here. Great for daytime awareness - plant the seed for tonight's trivia. "
            "High dwell time in morning lines."
        ),
        "placement_tip": (
            "Leave a small stack of cards or a flyer on community bulletin boards. "
            "Morning coffee crowd is your advance marketing team."
        ),
    },
    {
        "id": 6,
        "name": "UNC Campus - South Building / Polk Place",
        "lat": 35.9117,
        "lon": -79.0510,
        "address": "Cameron Ave & S Columbia St",
        "foot_traffic": 9,
        "dwell_time": 7,
        "visibility": 7,
        "student_density": 10,
        "best_times": ["10am-4pm"],
        "rationale": (
            "Central campus quad. Massive student foot traffic between classes. "
            "People sit on the grass, eat lunch, and hang out. Daytime-only but "
            "huge reach for planting awareness."
        ),
        "placement_tip": (
            "Chalk the sidewalk (if allowed) or post on departmental bulletin boards "
            "in nearby buildings. Hand out cards between classes."
        ),
    },
    {
        "id": 7,
        "name": "Target / University Place Bus Stop",
        "lat": 35.9218,
        "lon": -79.0444,
        "address": "201 S Estes Dr",
        "foot_traffic": 7,
        "dwell_time": 9,
        "visibility": 8,
        "student_density": 7,
        "best_times": ["3pm-7pm"],
        "rationale": (
            "Students waiting for the bus have extended dwell time with nothing to do. "
            "Bus shelters are natural billboard spaces. Captures off-campus students "
            "who shop at Target/Trader Joe's."
        ),
        "placement_tip": (
            "Post inside the bus shelter if allowed. A weatherproof flyer here "
            "gets dozens of eyeballs per hour from bored bus-waiters."
        ),
    },
    {
        "id": 8,
        "name": "Linda's Bar & Grill Sidewalk",
        "lat": 35.9129,
        "lon": -79.0572,
        "address": "203 E Franklin St",
        "foot_traffic": 7,
        "dwell_time": 6,
        "visibility": 8,
        "student_density": 8,
        "best_times": ["6pm-12am"],
        "rationale": (
            "Popular bar with outdoor seating. Sidewalk traffic passes right by "
            "diners and drinkers. People sitting outside are relaxed and receptive "
            "to scanning QR codes."
        ),
        "placement_tip": (
            "Ask if you can leave cards on the outdoor tables or post a flyer "
            "near the entrance. Outdoor diners are a captive audience."
        ),
    },
    {
        "id": 9,
        "name": "Carolina Coffee Shop Area",
        "lat": 35.9133,
        "lon": -79.0545,
        "address": "138 E Franklin St",
        "foot_traffic": 8,
        "dwell_time": 9,
        "visibility": 7,
        "student_density": 9,
        "best_times": ["8am-5pm"],
        "rationale": (
            "Historic diner, always busy. Students and locals linger over coffee and "
            "meals. Bulletin board inside is well-read. Daytime crowd that will "
            "remember trivia night when evening comes."
        ),
        "placement_tip": (
            "Post on the community bulletin board inside. Leave a few cards "
            "at the register if staff allows."
        ),
    },
    {
        "id": 10,
        "name": "Varsity Theatre / Rafferty's Sidewalk",
        "lat": 35.9135,
        "lon": -79.0559,
        "address": "123 E Franklin St",
        "foot_traffic": 8,
        "dwell_time": 5,
        "visibility": 9,
        "student_density": 8,
        "best_times": ["5pm-11pm"],
        "rationale": (
            "High-visibility stretch of Franklin with bright signage and steady "
            "evening foot traffic. People slow down here to look at the Varsity "
            "marquee and restaurant menus."
        ),
        "placement_tip": (
            "Tape a flyer to the utility pole nearest the Varsity marquee. "
            "People are already looking up - put your QR code in their sight line."
        ),
    },
]


def get_ranked_spots(time_of_day="evening", top_n=8):
    """
    Rank spots by a weighted composite score.
    Evening weighting favors foot_traffic and student_density.
    Daytime weighting favors dwell_time and visibility.
    """
    for spot in FRANKLIN_STREET_SPOTS:
        if time_of_day == "evening":
            score = (
                spot["foot_traffic"] * 0.35
                + spot["dwell_time"] * 0.20
                + spot["visibility"] * 0.25
                + spot["student_density"] * 0.20
            )
        else:
            score = (
                spot["foot_traffic"] * 0.25
                + spot["dwell_time"] * 0.30
                + spot["visibility"] * 0.25
                + spot["student_density"] * 0.20
            )
        spot["composite_score"] = round(score, 2)

    ranked = sorted(
        FRANKLIN_STREET_SPOTS, key=lambda s: s["composite_score"], reverse=True
    )
    return ranked[:top_n]
