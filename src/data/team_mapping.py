"""Team name mapping for canonicalization."""

# Common aliases mapping to canonical names
TEAM_ALIASES = {
    "Ole Miss": "Mississippi",
    "Mississippi": "Mississippi",
    "UConn": "UConn",
    "Connecticut": "UConn",
    "UMass": "Massachusetts",
    "Massachusetts": "Massachusetts",
    "LA Tech": "Louisiana Tech",
    "Louisiana Tech": "Louisiana Tech",
    "UTEP": "UTEP",
    "Texas-El Paso": "UTEP",
    "UTSA": "UTSA",
    "UT San Antonio": "UTSA",
    "UCF": "UCF",
    "Central Florida": "UCF",
    "USF": "South Florida",
    "South Florida": "South Florida",
    "FAU": "Florida Atlantic",
    "Florida Atlantic": "Florida Atlantic",
    "FIU": "Florida International",
    "Florida International": "Florida International",
    "BYU": "BYU",
    "Brigham Young": "BYU",
    "TCU": "TCU",
    "Texas Christian": "TCU",
    "SMU": "SMU",
    "Southern Methodist": "SMU",
    "UNLV": "UNLV",
    "Nevada-Las Vegas": "UNLV",
    "Hawai'i": "Hawai'i",
    "Hawaii": "Hawai'i",
    "Miami (FL)": "Miami",
    "Miami (OH)": "Miami (OH)",
    "Miami": "Miami",
    "San Jose State": "San José State",
    "San José State": "San José State",
    "Appalachian State": "App State",
    "App State": "App State",
    "Sam Houston State": "Sam Houston",
    "Sam Houston": "Sam Houston",
    "Southern Mississippi": "Southern Miss",
    "Southern Miss": "Southern Miss",
    "Middle Tennessee State": "Middle Tennessee",
    "Middle Tennessee": "Middle Tennessee",
    "California": "California",
    "Cal": "California",
    "California Golden": "California",
}


def to_canonical(name: str) -> str:
    """Convert team name to canonical form.

    Args:
        name: Team name (may be alias)

    Returns:
        Canonical team name
    """
    if not name:
        return name
    
    # Try exact match first
    if name in TEAM_ALIASES:
        return TEAM_ALIASES[name]
    
    # Try case-insensitive match
    name_lower = name.lower()
    for alias, canonical in TEAM_ALIASES.items():
        if alias.lower() == name_lower:
            return canonical
    
    # Strip common mascot names from Odds API format
    # e.g., "Florida State Seminoles" → "Florida State"
    mascots = [
        "Seminoles", "Wolfpack", "Rebels", "Rainbow Warriors", "Golden Hurricane",
        "Black Knights", "Blue Hens", "Demon Deacons", "Jayhawks", "Cyclones",
        "Cardinals", "Mustangs", "Hurricanes", "Hokies", "Golden Gophers",
        "Wildcats", "Tigers", "Sooners", "Scarlet Knights", "Buckeyes",
        "Wolverines", "Terrapins", "Bulls", "Blazers", "Sun Devils",
        "Buffaloes", "Bears", "Cougars", "Fighting Illini", "Hawkeyes",
        "Trojans", "Ducks", "Pirates", "Roadrunners", "Yellow Jackets",
        "Volunteers", "Huskies", "Nittany Lions", "Utes", "Razorbacks",
        "Longhorns", "Mean Green", "Broncos", "Spartans", "Aztecs",
        "Hoosiers", "Aggies", "Eagles", "Knights", "RedHawks", "Chippewas",
        "Zips", "Falcons", "Warhawks", "Red Wolves", "Ragin' Cajuns",
        "Mountaineers", "Hilltoppers", "Thundering Herd", "Bulldogs",
        "Owls", "Hatters", "Monarchs", "Chanticleers", "Gamecocks",
        "Mavericks", "Blue Raiders", "49ers", "Golden Panthers", "Minutemen",
        "Bobcats", "Rockets", "Herd", "Phoenix", "Flames", "Colonels",
        "Jaguars", "Bearkats", "Panthers", "Ragin Cajuns", "Fighting Hawks",
        "Penguins", "Great Danes", "Hornets", "Tritons", "Grizzlies",
        "Vandals", "Redhawks", "Miners", "Cardinals", "Rainbow Warriors",
        "Wolf Pack", "Cornhuskers", "Badgers", "Scarlet Knights", "Tar Heels",
        "Blue Devils", "Orange", "Fighting Irish", "Commodores", "Gators",
        "Crimson Tide", "War Eagles", "Lions", "Salukis", "Dukes", "Cowboys",
        "Golden", "Cardinal", "Bearcats", "Bruins", "Boilermakers", "Rams",
        "Crimson", "Golden Eagles", "Red Raiders", "Green Wave", "Paladins",
        "Midshipmen", "Tribe", "Bison", "Catamounts", "Matadors", "Horned Frogs",
        "Lobos", "Beavers", "Cavaliers", "Spiders", "Mocs", "Terriers",
        "Skyhawks", "Gamecocks", "Mocs", "Bears", "Bison", "Panthers",
        "Penguins", "Racers", "Sycamores", "Leathernecks", "Salukis",
        "Redbirds", "Braves", "Vikings", "Thunderbirds", "Lumberjacks",
        "Hornets", "Aggies", "Mustangs", "Bengals", "Vandals", "Eagles",
        "Wildcats", "Grizzlies", "Bobcats", "Golden Flashes"
    ]
    
    for mascot in mascots:
        if name.endswith(f" {mascot}"):
            stripped_name = name[:-len(mascot)-1].strip()
            # Recursively check if the stripped name is an alias
            return to_canonical(stripped_name)
    
    # Return original if no transformation applied
    return name


