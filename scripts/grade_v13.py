import pandas as pd
import io

# Load V13 picks
try:
    picks_df = pd.read_csv('reports/2025_w13_picks.csv')
except:
    print("Error: Could not read picks CSV")
    exit()

# Actual scores (same as before)
csv_data = """
,homeTeam,awayTeam,homePoints,awayPoints
0,Ohio,Massachusetts,42,14
1,Bowling Green,Akron,16,19
2,Northern Illinois,Western Michigan,19,35
3,Kent State,Central Michigan,16,28
4,Buffalo,Miami (OH),20,37
5,SE Louisiana,Nicholls,38,26
6,Northwestern State,Stephen F. Austin,14,62
7,Arkansas State,Louisiana,30,34
8,Curry College,Merchant Marine Academy,24,27
9,NC State,Florida State,21,11
10,UNLV,Hawai'i,38,10
11,Long Island University,Wagner,24,17
12,Brockport,Geneva,46,10
13,Texas A&M,Samford,48,0
14,Virginia Tech,Miami,17,34
15,Yale,Harvard,45,28
16,Army,Tulsa,25,26
17,Oklahoma,Missouri,17,6
18,Ohio State,Rutgers,42,9
19,Illinois College,Aurora,14,49
20,Northwestern,Minnesota,38,35
21,Delaware Valley,Dickinson (PA),14,13
22,Iowa State,Kansas,38,14
23,St John Fisher University,Rensselaer,24,35
24,Carnegie Mellon,Misericordia,24,17
25,SMU,Louisville,38,6
26,Stony Brook,Bryant,35,28
27,Brown,Dartmouth,35,28
28,Morgan State,North Carolina Central,14,33
29,Central Connecticut,Mercyhurst,35,28
30,Merrimack,Fordham,27,26
31,Lycoming,Washington and Lee,12,14
32,VMI,Western Carolina,6,48
33,Monmouth,UAlbany,24,31
34,Wake Forest,Delaware,52,14
35,Lafayette,Lehigh,32,42
36,Georgia,Charlotte,35,3
37,East Tennessee State,The Citadel,28,26
38,William & Mary,Richmond,21,28
39,Pennsylvania,Princeton,17,6
40,Ursinus,Lebanon Valley,31,13
41,Delaware State,South Carolina State,17,28
42,Alabama State,Arkansas-Pine Bluff,44,13
43,Stonehill,St. Francis (PA),20,10
44,Indiana State,Murray State,17,31
45,Illinois State,Southern Illinois,7,37
46,Arizona,Baylor,41,17
47,James Madison,Washington State,24,20
48,Georgia Southern,Old Dominion,10,45
49,Stetson,San Diego,8,42
50,Utica,Rowan,20,26
51,Rhode Island,Hampton,38,10
52,Towson,Campbell,35,31
53,Drake,Morehead State,17,10
54,Tennessee Tech,UT Martin,20,17
55,Presbyterian,Marist,29,25
56,Butler,Valparaiso,27,20
57,New Hampshire,Maine,33,27
58,Cornell,Columbia,12,29
59,Wabash College,Ohio Northern,32,31
60,Colgate,Bucknell,38,19
61,Davidson,Dayton,14,42
62,Villanova,Sacred Heart,34,10
63,SUNY Maritime,Hobart College,14,42
64,Gardner-Webb,Western Illinois,24,29
65,Wofford,Chattanooga,35,13
66,Northern Colorado,Portland State,24,13
67,Kennesaw State,Missouri State,41,34
68,North Alabama,Southern Utah,34,36
69,Charleston Southern,Tennessee State,7,6
70,Robert Morris,Duquesne,17,20
71,North Dakota,South Dakota State,31,34
72,Northern Iowa,Youngstown State,32,35
73,Auburn,Mercer,62,17
74,Montana,Montana State,28,31
75,Southeast Missouri State,Lindenwood,13,30
76,Wyoming,Nevada,7,13
77,Alabama,Eastern Illinois,56,0
78,Toledo,Ball State,38,9
79,Elon,North Carolina A&T,55,17
80,App State,Marshall,26,24
81,Prairie View A&M,Mississippi Valley State,59,6
82,Houston Christian,Incarnate Word,10,31
83,Wisconsin-Stout,Washington University (St. Louis),31,23
84,UTEP,New Mexico State,31,34
85,Florida Atlantic,UConn,45,48
86,UAB,South Florida,18,48
87,Texas Southern,Alabama A&M,24,7
88,Middle Tennessee,Sam Houston,31,17
89,Louisiana Tech,Liberty,34,28
90,Weber State,Northern Arizona,48,28
91,Texas,Arkansas,52,37
92,Iowa,Michigan State,20,17
93,Vanderbilt,Kentucky,45,17
94,Alcorn State,Jackson State,21,27
95,North Dakota State,St. Thomas (MN),62,7
96,Florida A&M,Bethune-Cookman,34,38
97,South Alabama,Southern Miss,42,35
98,UTSA,East Carolina,58,24
99,North Carolina,Duke,25,32
100,Florida International,Jacksonville State,27,21
101,Notre Dame,Syracuse,70,7
102,Oregon,USC,42,27
103,Howard,Norfolk State,44,15
104,Temple,Tulane,13,37
105,Houston,TCU,14,17
106,UCF,Oklahoma State,17,14
107,Maryland,Michigan,20,45
108,Utah,Kansas State,51,47
109,Troy,Georgia State,31,19
110,Utah Tech,Eastern Kentucky,10,33
111,UC Davis,Sacramento State,31,27
112,Shenandoah,Wilkes,35,37
113,Lamar,McNeese,19,21
114,Holy Cross,Georgetown,42,7
115,Idaho,Idaho State,16,37
116,South Carolina,Coastal Carolina,51,7
117,Clemson,Furman,45,10
118,Texas State,UL Monroe,31,14
119,Central Arkansas,Abilene Christian,28,49
120,Tarleton State,Austin Peay,45,44
121,Cal Poly,Eastern Washington,43,34
122,Westminster (PA),Mount St. Joseph,40,21
123,UT Rio Grande Valley,East Texas A&M,33,14
124,Air Force,New Mexico,3,20
125,Georgia Tech,Pittsburgh,28,42
126,Boise State,Colorado State,49,21
127,Penn State,Nebraska,37,10
128,Wisconsin,Illinois,27,10
129,Florida,Tennessee,11,31
130,Stanford,California,31,10
131,Rice,North Texas,24,56
132,LSU,Western Kentucky,13,10
133,Colorado,Arizona State,17,42
134,Cincinnati,BYU,14,26
135,Fresno State,Utah State,17,28
136,San Diego State,San José State,25,3
137,UCLA,Washington,14,48
138,Framingham State,Lagrange College,21,24
139,Springfield,Cortland,21,7
140,Kutztown University,Bentley,52,0
141,Muhlenberg,Union (NY),34,26
142,Susquehanna,Washington & Jefferson,38,32
143,Hanover College,Grove City College,23,15
144,Concordia-Wisconsin,Coe College,7,44
145,Ferris State,Northwood (MI),65,14
146,Johnson C Smith,Frostburg State,7,21
147,Wheaton,Crown College,76,14
148,Newberry,Kentucky State,45,24
149,Virginia Union,PennWest California,24,27
150,Indiana-Pennsylvania,Assumption,20,23
151,Ashland,Minnesota Duluth,32,7
152,Findlay,Minnesota State Mankato,14,37
153,Albany State GA,Valdosta State,35,30
154,West Florida,North Greenville,43,19
155,Wingate,Benedict College,24,25
156,Pittsburg St,Chadron St,21,17
157,Harding University,Northwest Missouri St,38,16
158,Indianapolis,Truman State,57,14
159,Whitworth,Chapman,16,18
160,CSU Pueblo,UT Permian Basin,24,37
161,Central Washington,Western Colorado,20,27
"""

actual_df = pd.read_csv(io.StringIO(csv_data))

# Clean team names for merging
from src.data.team_mapping import to_canonical
actual_df["home_team"] = actual_df["homeTeam"].apply(to_canonical)
actual_df["away_team"] = actual_df["awayTeam"].apply(to_canonical)

# Merge
merged = picks_df.merge(actual_df, on=["home_team", "away_team"], how="inner")

print(f"Grading {len(merged)} games...")

correct = 0
total = 0
wrong_picks = []

for _, row in merged.iterrows():
    market_spread = row["market_spread_home"]
    if pd.isna(market_spread):
        continue
        
    home_margin = row["homePoints"] - row["awayPoints"]
    ats_result = "Home" if home_margin > -market_spread else "Away"
    if home_margin == -market_spread:
        ats_result = "Push"
        
    # Get model pick using ATS Pick string or Fair Spread
    ats_pick_str = str(row.get("ATS Pick", ""))
    if "N/A" in ats_pick_str:
        continue
        
    # We can parse the ATS Pick string: "Team Name (-X.X) (Conf/10)"
    # Or recalculate edge. Let's use the pick string logic implicitly by checking Edge column
    # Edge > 0 = Home, Edge < 0 = Away
    edge = row.get("edge_spread_pts", 0)
    
    if edge > 0:
        model_pick = "Home"
    elif edge < 0:
        model_pick = "Away"
    else:
        model_pick = "Pass"
        
    if ats_result == "Push":
        continue
        
    total += 1
    if model_pick == ats_result:
        correct += 1
    else:
        wrong_picks.append({
            "Matchup": f"{row['away_team']} @ {row['home_team']}",
            "Spread": market_spread,
            "Score": f"{row['awayPoints']}-{row['homePoints']}",
            "Margin": home_margin,
            "Result": ats_result,
            "Pick": model_pick,
            "Fair Spread": row["fair_spread_home"],
            "Edge": edge
        })

print(f"Accuracy: {correct}/{total} ({correct/total:.1%})")
print("\nWrong Picks:")
for p in wrong_picks:
    print(p)

