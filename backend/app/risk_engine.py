def calculate_risk(reading):
    risk = 0
    messages = []

    if reading.dissolved_oxygen < 4:
        risk += 40
        messages.append("Low Dissolved Oxygen")

    if reading.ammonia > 0.5:
        risk += 30
        messages.append("High Ammonia")

    if reading.temperature > 32:
        risk += 20
        messages.append("High Temperature")

    health_score = max(0, 100 - risk)

    return health_score, messages
