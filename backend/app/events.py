from .schemas import EventCode, ReferenceStatus

EVENTS = {
    EventCode.M100: {
        "label": "100 metres",
        "phases": ["acceleration", "max_velocity"],
        "reference_status": ReferenceStatus.CALIBRATED,
        "features": ["acceleration", "maximum velocity", "step mechanics"],
    },
    EventCode.M200: {
        "label": "200 metres",
        "phases": ["curve", "transition", "speed_endurance"],
        "reference_status": ReferenceStatus.PENDING,
        "features": ["curve mechanics", "straight transition", "speed endurance"],
    },
    EventCode.M400: {
        "label": "400 metres",
        "phases": ["pacing", "curve", "fatigue"],
        "reference_status": ReferenceStatus.PENDING,
        "features": ["100m splits", "fatigue decay", "speed reserve"],
    },
}

STAGES_100M = [
    ("T3", "Trained athletes", 8.819, "AthleticsPose sprint cohort"),
    ("T1", "World-class field", 11.584, "London 2017 biomechanics report"),
    ("T2", "Record benchmark", 12.215, "Berlin 2009 biomechanics reference"),
]

