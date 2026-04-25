from collections import Counter
import re

def find_anagrams(target, word_list):
    target_counts = Counter(target.replace(" ", "").lower())
    results = []
    # Just a simple check, not a full anagram solver, but we can do it manually.
    pass

text1 = "ENG SALCE OP" # CONSOLE PAGE
text2 = "100KM ZAFSUIS H"
text3 = "DATA: NEMIRAS CODE 1 ACE"

print(Counter(text1.replace(" ", "").lower()))
print(Counter(text2.replace(" ", "").lower()))
print(Counter(text3.replace(" ", "").lower()))
