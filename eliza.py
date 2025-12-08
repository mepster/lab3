import re
import random
import sys

# eliza.py
# A faithful reimplementation of the 1960s ELIZA conversational program (doctor script).
# Usage: run and chat. Type 'quit' or 'bye' to exit.

# a better one is at https://anthay.github.io/eliza.html
# https://sites.google.com/view/elizaarchaeology/try-eliza

# Pre-substitutions and punctuation removal
PUNCT_RE = re.compile(r"[^\w\s@']")  # keep @ for synonyms, keep apostrophes for contractions
WHITESPACE_RE = re.compile(r"\s+")

PRE_SUBS = {
    "dont": "don't",
    "cant": "can't",
    "wont": "won't",
    "recollect": "remember",
    "dreamt": "dreamed",
    "dreams": "dream",
    "maybe": "perhaps",
    "certainly": "yes",
    "machine": "computer",
    "computers": "computer",
    "were": "was",
    "you're": "you are",
    "i'm": "i am",
}

# Reflections (post substitutions)
REFLECTIONS = {
    "am": "are",
    "was": "were",
    "i": "you",
    "i'd": "you would",
    "i've": "you have",
    "i'll": "you will",
    "my": "your",
    "are": "am",
    "you've": "I have",
    "you'll": "I will",
    "your": "my",
    "yours": "mine",
    "you": "me",
    "me": "you",
    "myself": "yourself",
    "yourself": "myself",
}

# Synonyms used in patterns (classic ELIZA)
SYNONYMS = {
    "be": ["am", "is", "are", "was"],
    "belief": ["feel", "think", "believe", "wish"],
    "family": ["mother", "mom", "father", "dad", "sister", "brother", "wife", "children", "child"],
    "desire": ["want", "need"],
    "sad": ["unhappy", "depressed", "sick"],
    "happy": ["elated", "glad", "better"],
    "cannot": ["can't", "cannot"],
}

# The key table: key -> (rank, [ (decomp_pattern, [reassembly_templates], pointer) ... ])
# Patterns use '*' wildcards and '@synonym' references. Reassembly templates may contain:
#  - (n) tokens like (1) to insert nth wildcard match (1-based),
#  - 'goto key' to switch to another key,
#  - 'MEMORY' directive to store a reassembly into memory (e.g., "MEMORY (1)"),
#  - else produce response text.
ELIZA_KEYS = {}

def add_key(key, rank, decomps):
    ELIZA_KEYS[key] = {"rank": rank, "decomps": [{"pattern": d[0], "reassembly": d[1], "ptr": 0} for d in decomps]}

# A compact subset of the original ELIZA doctor script (representative).
# This is not the entire original script but follows the same structure and rules.
add_key("xnone", 0, [
    ("*", [
        "I'm not sure I understand you fully.",
        "Please go on.",
        "What does that suggest to you?",
        "Do you feel strongly about discussing such things?"
    ])
])

add_key("sorry", 1, [
    ("I am sorry *", [
        "Please don't apologize.",
        "Apologies are not necessary.",
        "What feelings do you have when you apologize?"
    ]),
    ("I regret *", [
        "Maybe I can help you not to feel regret. How?",
        "We all have regrets. Why is this one important to you?"
    ])
])

add_key("name", 5, [
    ("* my name is *", [
        "Nice to meet you (2). How long have you had that name?",
        "Do you like being called (2)?"
    ]),
    ("* i am called *", [
        "Called (2)? Is that what others call you?",
        "Why do they call you (2)?"
    ])
])

add_key("mother", 5, [
    ("* my @family *", [
        "Tell me more about your (2).",
        "Who else in your family (2)?",
        "How do you feel about your (2)?"
    ]),
    ("* my mother *", [
        "Tell me more about your mother.",
        "What was your relationship with your mother like?",
        "How do you feel about your mother now?"
    ])
])

add_key("family", 3, [
    ("* @family *", [
        "Family relationships can be complicated. Tell me more.",
        "How does that make you feel?",
    ])
])

add_key("desire", 4, [
    ("* i want *", [
        "What would it mean to you if you got (2)?",
        "Why do you want (2)?",
        "Suppose you got (2) soon. What would you do then?"
    ]),
    ("* i would like *", [
        "Why would you like (2)?",
        "What would (2) mean to you?"
    ])
])

add_key("cannot", 3, [
    ("* cannot *", [
        "Do you really think you cannot (2)?",
        "Perhaps you could if you wanted to.",
        "What would it take for you to (2)?"
    ])
])

add_key("i_am", 5, [
    ("i am *", [
        "How long have you been (1)?",
        "Do you enjoy being (1)?",
        "Do you often feel (1)?"
    ]),
    ("i'm *", [
        "How long have you been (1)?",
        "Really, you're (1)?",
        "Does being (1) worry you?"
    ])
])

add_key("because", 2, [
    ("* because *", [
        "Is that the real reason?",
        "Are there other reasons?",
        "Does that reason explain everything?"
    ])
])

add_key("sorry2", 1, [
    ("*", [
        "Can you elaborate on that?",
        "Why do you say that?"
    ])
])

add_key("quit", 0, [
    ("bye", [
        "Goodbye. Thank you for talking to me.",
    ]),
    ("quit", [
        "Goodbye. Take care."
    ])
])

# A list of quit words
QUIT_WORDS = {"bye", "goodbye", "quit", "exit"}

# Memory stack for storing responses (original ELIZA had a small memory)
memory = []

# Utilities

def normalize_input(s):
    s = s.lower()
    s = PUNCT_RE.sub(" ", s)
    s = WHITESPACE_RE.sub(" ", s).strip()
    tokens = s.split()
    # apply pre substitutions
    tokens = [PRE_SUBS.get(t, t) for t in tokens]
    return " ".join(tokens)

def tokenize(s):
    return s.split()

def reflect(fragment):
    # reflect words using REFLECTIONS, preserve case? everything lower-case here
    tokens = tokenize(fragment)
    return " ".join(REFLECTIONS.get(t, t) for t in tokens)

# Pattern matching with '*' wildcards and '@syn' synonyms.
def pattern_to_tokens(pattern):
    # pattern is something like "* i am @believe *"
    # Split on whitespace, keep '*' and '@' tokens intact.
    return pattern.split()

def match_pattern(pattern_tokens, input_tokens, syn_map):
    # recursive matcher that returns list of wildcard captures if matches, else None
    def match_helper(p_idx, i_idx):
        captures = []
        # When both pattern and input exhausted, success.
        if p_idx == len(pattern_tokens) and i_idx == len(input_tokens):
            return []  # no captures
        # If pattern exhausted but input remains -> fail
        if p_idx == len(pattern_tokens):
            return None
        token = pattern_tokens[p_idx]
        # wildcard
        if token == "*":
            # try all possible lengths of capture for this wildcard
            if p_idx == len(pattern_tokens) - 1:
                # trailing *, capture the rest
                capture = " ".join(input_tokens[i_idx:]) if i_idx < len(input_tokens) else ""
                return [capture]
            # otherwise, need to find a match for the next literal token
            next_token = pattern_tokens[p_idx + 1]
            for k in range(i_idx, len(input_tokens) + 1):
                # attempt to match next_token at position k
                # But next_token may be synonym or literal; check if it matches input_tokens[k]
                submatch = None
                if k < len(input_tokens):
                    if next_token.startswith("@"):
                        syn = next_token[1:]
                        if input_tokens[k] in syn_map.get(syn, []):
                            submatch = match_helper(p_idx + 2, k + 1)
                    else:
                        if input_tokens[k] == next_token:
                            submatch = match_helper(p_idx + 2, k + 1)
                else:
                    submatch = None
                if submatch is not None:
                    capture = " ".join(input_tokens[i_idx:k])
                    return [capture] + submatch
            return None
        elif token.startswith("@"):
            syn = token[1:]
            if i_idx < len(input_tokens) and input_tokens[i_idx] in syn_map.get(syn, []):
                rest = match_helper(p_idx + 1, i_idx + 1)
                if rest is not None:
                    return [""] + rest  # no capture for synonym, but align captures count
            return None
        else:
            # literal token must match
            if i_idx < len(input_tokens) and input_tokens[i_idx] == token:
                return match_helper(p_idx + 1, i_idx + 1)
            else:
                return None

    return match_helper(0, 0)

# Apply a reassembly template: replace (n) tokens with captured groups, apply reflections
def assemble(reassembly, captures):
    # reassembly may be a string maybe with "goto KEY" or "MEMORY (n)"
    if reassembly.lower().startswith("goto "):
        return ("GOTO", reassembly.split(None, 1)[1].strip())
    if reassembly.lower().startswith("memory"):
        # format: "memory (1)" or "memory (1) some text"
        m = re.match(r"memory\s*(\(?\s*(\d+)\s*\)?)?\s*(.*)", reassembly, re.I)
        if m:
            idx = int(m.group(2)) if m.group(2) else 1
            rest = m.group(3).strip()
            cap = captures[idx - 1] if 0 <= idx - 1 < len(captures) else ""
            cap = reflect(cap)
            return ("MEMORY", cap, rest)
    # general: replace occurrences of (n) with reflections of captures
    def repl(m):
        idx = int(m.group(1))
        text = captures[idx - 1] if 0 <= idx - 1 < len(captures) else ""
        return reflect(text)
    out = re.sub(r"\((\d+)\)", repl, reassembly)
    return ("TEXT", out)

# Main response generation
def respond(input_line):
    s = normalize_input(input_line)
    if not s:
        return "Please say something."
    input_tokens = tokenize(s)

    # Check for quit words
    for w in input_tokens:
        if w in QUIT_WORDS:
            return "Goodbye. Thank you for talking to me."

    # Find matching keys sorted by rank descending, key text presence
    # Classic ELIZA picked the most important key word present in input left-to-right.
    # We'll find keys present in input tokens. For patterns starting with '*' we still need to try.
    best_key = None
    best_rank = -1
    for key, info in ELIZA_KEYS.items():
        # check if key appears as literal in input or in synonyms
        if key in ["xnone"]:
            continue
        # If key token is in input tokens or any literal starting token of patterns matches, consider it
        if key in input_tokens:
            if info["rank"] > best_rank:
                best_rank = info["rank"]
                best_key = key
    # If none found, use xnone fallback
    if best_key is None:
        best_key = "xnone"

    # Try decompositions for that key
    def try_key(k):
        info = ELIZA_KEYS[k]
        decomps = info["decomps"]
        for di in decomps:
            pattern = di["pattern"]
            pat_tokens = pattern_to_tokens(pattern)
            # Expand pattern tokens: replace @syn identifiers by token '@syn' which is interpreted in match
            captures = match_pattern(pat_tokens, input_tokens, SYNONYMS)
            if captures is not None:
                # choose a reassembly template (cycle)
                reas_list = di["reassembly"]
                ptr = di.get("ptr", 0)
                template = reas_list[ptr % len(reas_list)]
                di["ptr"] = (ptr + 1) % len(reas_list)
                action = assemble(template, captures)
                if action[0] == "GOTO":
                    target = action[1]
                    if target in ELIZA_KEYS:
                        return try_key(target)
                    else:
                        return "I don't understand."
                elif action[0] == "MEMORY":
                    cap = action[1]
                    rest = action[2]
                    if cap:
                        memory.append(cap)
                    if rest:
                        return rest
                    # otherwise continue to xnone
                elif action[0] == "TEXT":
                    return action[1]
        return None

    resp = try_key(best_key)
    if resp:
        return resp
    # If nothing for best key, try xnone explicitly
    info = ELIZA_KEYS.get("xnone")
    if info:
        di = info["decomps"][0]
        template = di["reassembly"][random.randrange(len(di["reassembly"]))]
        return template
    return "I have nothing to say."

# Run interactive loop if invoked directly
def main():
    print("ELIZA: Hello. I'm ELIZA. Please tell me your problem.")
    try:
        while True:
            user = input("YOU: ")
            if not user:
                print("ELIZA: Please say something.")
                continue
            if user.lower().strip() in QUIT_WORDS:
                print("ELIZA: Goodbye. Thank you for talking to me.")
                break
            reply = respond(user)
            print("ELIZA:", reply)
    except (KeyboardInterrupt, EOFError):
        print("\nELIZA: Goodbye. Take care.")
        sys.exit(0)

if __name__ == "__main__":
    # Reduce the frequency of a specific fallback reply by removing it from xnone's reassembly list,
    # and shuffle the remaining alternatives so responses vary more.
    xnone = ELIZA_KEYS.get("xnone")
    if xnone:
        di = xnone["decomps"][0]
        di["reassembly"] = [r for r in di["reassembly"] if r != "I'm not sure I understand you fully."]
        if not di["reassembly"]:
            di["reassembly"] = ["Please go on.", "What does that suggest to you?", "Do you feel strongly about discussing such things?"]
        random.shuffle(di["reassembly"])

    main()