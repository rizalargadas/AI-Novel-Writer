import hashlib
import re
import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI

# Load API key from .env
load_dotenv()

client = OpenAI()

# Folders
BASE_DIR = Path(".")
OUTPUTS_DIR = BASE_DIR / "outputs"
CHAPTERS_DIR = BASE_DIR / "chapters"
PUBLISHING_DIR = BASE_DIR / "publishing"

OUTPUTS_DIR.mkdir(exist_ok=True)
CHAPTERS_DIR.mkdir(exist_ok=True)
PUBLISHING_DIR.mkdir(exist_ok=True)

WRITING_PHILOSOPHY = """
WRITING PHILOSOPHY (internalize this before every chapter)

These are the craft principles that separate memorable fiction from forgettable prose.
Violating them is the most common reason readers say a story "has no soul."

1. SHOW, DON'T TELL — BUT GO DEEPER THAN THE CLICHÉ
Do not write: "She was nervous."
Write the nervous: the rehearsed sentence dissolving before it reaches her lips,
the way she smooths the same wrinkle in her skirt three times.

Every emotion must have a physical body. Ground feelings in sensation, gesture,
and involuntary reaction.

2. SCENE OVER SUMMARY
Do not summarize what happened. Put the reader inside the moment it happens.
Bad: "They argued for an hour and she left angry."
Good: The argument lives on the page — the specific words, the silences,
the thing she almost said and didn't.

If a moment matters to the character, it must cost the reader something too.
Don't skip the hard scenes. Slow down exactly where it hurts.

3. DIALOGUE MUST DO DOUBLE WORK
Every line of dialogue should carry subtext. Characters rarely say exactly what
they mean — they deflect, overexplain, go quiet at the wrong moment, joke when
they're breaking.

Let silence and indirection do the emotional labor. What is NOT said is often
the most important line.

4. SPECIFICITY IS SOUL
Vague writing feels hollow. Specific writing feels true.
Not: "a nice restaurant" — the exact name, the candle that kept guttering,
the way the menu was printed in a font too small for the lighting.
Not: "she smelled his cologne" — which cologne, what it reminded her of,
whether it made things better or worse.

Sensory and setting-specific detail transforms a plot into a world.
Earn the reader's trust with precision.

5. CHARACTER INTERIORITY — THE INNER LIFE IS THE REAL STORY
Between every action and reaction, there is a thought, a memory, a contradiction.
Let the reader live inside the character's head — not just observing them,
but thinking alongside them.

Readers don't fall in love with plot events. They fall in love with a character's
specific way of seeing the world. Protect and develop that voice relentlessly.

6. PACING IS EMOTIONAL, NOT MECHANICAL
Short sentences accelerate. Long sentences breathe. Paragraph breaks create
weight. A single sentence on its own line can stop a reader's heart.

Vary your rhythm intentionally. Tension scenes move fast. Intimate scenes slow
almost to stillness. Do not write every scene at the same tempo.

7. AVOID THESE SPECIFIC FAILURE MODES
- Emotion-labeling: "She felt sad." / "He was furious." Always replace with
  physical or behavioral rendering.
- Chapter padding: scenes that exist only to relay information, with no emotional stakes.
- On-the-nose dialogue: characters explaining feelings directly in ways real people never do.
- Symmetrical sentence structures that create a robotic rhythm.
- Adjective stacking instead of precise nouns and active verbs.
"""

def split_options(text, label="OPTION"):
    """
    Splits AI output into selectable chunks.
    Example labels: OPTION or ENDING.
    It ignores the RECOMMENDED OPTION / RECOMMENDED ENDING section.
    """
    pattern = rf"(?is)\b{label}\s+\d+\b.*?(?=\n\s*{label}\s+\d+\b|\n\s*RECOMMENDED\s+(OPTION|ENDING)\s*:|$)"
    parts = re.findall(pattern, text)

    # re.findall returns tuples because of the group in the lookahead.
    # This fixes that issue by using re.finditer instead.
    matches = re.finditer(pattern, text)
    clean_parts = [match.group(0).strip() for match in matches]

    return clean_parts

def extract_recommended_number(text, recommendation_label="OPTION", item_label="OPTION"):
    """
    Finds the recommended option/ending number from AI output.

    Example:
    RECOMMENDED OPTION:
    Option 4 is the strongest...

    RECOMMENDED ENDING:
    Ending 10 is the strongest...
    """
    recommended_section = re.search(
        rf"(?is)RECOMMENDED\s+{recommendation_label}\s*:.*",
        text
    )

    if not recommended_section:
        return None

    match = re.search(
        rf"(?i)\b{item_label}\s+(\d+)\b",
        recommended_section.group(0)
    )

    if match:
        return int(match.group(1))

    return None

def save_markdown(file_path, content):
    """Save text into a markdown file."""
    file_path = Path(file_path)
    file_path.parent.mkdir(exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def read_markdown(file_path):
    """Read markdown file if it exists."""
    file_path = Path(file_path)
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return ""


def ask_openai(prompt, model="gpt-5.5"):
    """
    Sends prompt to OpenAI.
    Use this only when the user clicks a button.
    """
    response = client.responses.create(
        model=model,
        reasoning={"effort": "low"},
        input=prompt
    )
    return response.output_text


def generate_pitch_prompt(story_idea, genre):
    return f"""
You are a bestselling LGBTQ+ fiction writer with expertise in {genre}.

Using the details below, generate 5 distinct story plot concepts.

Format each option exactly like this:

OPTION 1
Title:
Logline:
Summary:
Central Emotional Conflict:
Commercial Potential:

OPTION 2
Title:
Logline:
Summary:
Central Emotional Conflict:
Commercial Potential:

Continue until OPTION 5.

After all 5 options, add:
RECOMMENDED OPTION:
Briefly explain which option has the strongest commercial potential and why.

USER INPUT:
{story_idea}
"""


def generate_endings_prompt(pitch_text):
    return f"""
Based on the selected story plot below, create 10 different ending ideas.

Format each ending exactly like this:

ENDING 1
Title:
Ending Summary:
Emotional Payoff:
Reader Satisfaction:
Risk:

ENDING 2
Title:
Ending Summary:
Emotional Payoff:
Reader Satisfaction:
Risk:

Continue until ENDING 10.

After all 10 options, add:
RECOMMENDED ENDING:
Recommend the best ending according to:
- uniqueness
- emotional impact
- commercial reader satisfaction

SELECTED PLOT:
{pitch_text}
"""

def generate_expand_ending_prompt(pitch_text, selected_ending):
    return f"""
Based on the selected plot and selected ending below, expand the ending into a clean Markdown reference document.

This expanded ending will become the official confirmed ending for the novel.

Include:
- Ending Title
- Final Ending Summary
- Emotional Payoff
- Character Resolution
- Final Twist or Reveal, if applicable
- Last Scene Description
- Why This Ending Works
- Notes for Foreshadowing Earlier Chapters

Make the ending emotionally moving, unique, commercially satisfying, and structurally useful for later outlining.

SELECTED PLOT:
{pitch_text}

SELECTED ENDING:
{selected_ending}
"""

def generate_metadata_prompt(pitch_text, ending_text):
    return f"""
Using the story plot and confirmed ending below, create a clean Markdown metadata file.

Include:

1. Target Audience
Give a one-sentence explanation of the target audience.

2. Short Story Description
Write one short paragraph. Include:
- genre
- setting
- protagonist age bracket
- protagonist short description

PLOT:
{pitch_text}

CONFIRMED ENDING:
{ending_text}
"""


def generate_character_prompt(metadata_text, ending_text):
    return f"""
You are a genre-savvy fiction editor and character-development expert.

I am writing a novel to self-publish on Draft2Digital.

Story summary:
{metadata_text}

Confirmed ending:
{ending_text}

Create a complete character plan that supports the ending emotionally and structurally.

LEAD CHARACTERS — Full Deep-Dive Profile
For each lead character, provide:
- Name & Age
- Role
- Core Identity
- Wound
- Desire
- Need
- Fear
- Lie They Believe
- Truth They'll Learn
- Personality Snapshot
- Physical Description
- Voice & Mannerisms
- Key Relationships
- Arc

SUPPORTING CHARACTERS — Concise Functional Profile
For each supporting character, provide:
- Name, Age, Nationality
- Role
- Core Identity
- Desire / Fear
- Relationship to leads
- Story Function
- Voice in one sentence

Avoid these names and surnames:
Okafor, Marcus, Voss, Osei, Wren, Calloway, Soren, Sable, Chen, Mara, Dale, Vera, Calhoun, Petra, Maram, Priya, Eli, Nora, Cass, Vesper, Rhea

Format as a clean Markdown reference document.
"""


def generate_outline_prompt(metadata_text, character_text, ending_text):
    return f"""
You are a professional story architect and developmental editor.

Based on the story materials below, choose the strongest story structure from:
- Freytag's Pyramid
- The Hero's Journey
- Three Act Structure
- Dan Harmon's Story Circle
- Fichtean Curve
- Save the Cat Beat Sheet
- Seven-Point Story Structure

Then create a chapter-by-chapter outline.

Each chapter should include:
- Hooky chapter title
- Most important scene
- Main emotion
- Purpose
- Two-paragraph chapter description

Write as a clean Markdown reference document.

METADATA:
{metadata_text}

CHARACTER PROFILES:
{character_text}

CONFIRMED ENDING:
{ending_text}
"""


def generate_chapter_prompt(chapter_number, metadata_text, character_text, ending_text, outline_text):
    return f"""
Write Chapter {chapter_number} of the novel.

PROJECT CONTEXT:
Metadata:
{metadata_text}

Character Profiles:
{character_text}

Confirmed Ending:
{ending_text}

Outline:
{outline_text}

WRITING RULES:
- Write only the chapter.
- Format the chapter name as H1, example: # Chapter {chapter_number} - Chapter Title
- Do not summarize feelings; render them in scene.
- Use sensory detail, physical reaction, interiority, subtext, and emotionally specific dialogue.
- Do not include the audit in the chapter file.
- Do not use emojis.
- Do not use horizontal lines.
- Maintain continuity with the project documents.
- Mature scenes are permitted, but do not write erotica.
"""


# Streamlit UI
st.set_page_config(page_title="AI Novel Writing App", layout="wide")

st.title("AI Novel Writing App")
st.write("A simple app to automate your novel SOP step by step.")

st.sidebar.header("Settings")

model = st.sidebar.selectbox(
    "Model",
    [
        "gpt-5.5",
        "gpt-5.4",
        "gpt-5.4-mini"
    ],
    index=2
)

st.sidebar.caption("Use mini for cheaper drafts. Use stronger models for final chapter prose.")

page = st.sidebar.radio(
    "Choose Step",
    [
        "Step 1 - Pitch Maker",
        "Step 2 - Ending Plotting",
        "Step 3 - Metadata",
        "Step 4 - Character Profiles",
        "Step 5 - Outline",
        "Step 6 - Write Chapter"
    ]
)

if page == "Step 1 - Pitch Maker":
    st.header("Step 1 - Pitch Maker")

    genre = st.text_input("Genre", value="sapphic dark romance / psychological thriller")
    story_idea = st.text_area("Paste your story idea here", height=300)

    if st.button("Generate Pitch Options"):
        if not story_idea.strip():
            st.error("Please paste a story idea first.")
        else:
            prompt = generate_pitch_prompt(story_idea, genre)
            with st.spinner("Generating pitch options..."):
                result = ask_openai(prompt, model=model)

            st.session_state["pitch_options_raw"] = result
            st.session_state["pitch_options"] = split_options(result, label="OPTION")

            recommended_pitch_number = extract_recommended_number(
                result,
                recommendation_label="OPTION",
                item_label="OPTION"
            )

            st.session_state["recommended_pitch_number"] = recommended_pitch_number

    if "pitch_options_raw" in st.session_state:
        st.subheader("Generated Pitch Options")
        st.markdown(st.session_state["pitch_options_raw"])

        pitch_options = st.session_state.get("pitch_options", [])

        if pitch_options:
            recommended_pitch_number = st.session_state.get("recommended_pitch_number")

            default_index = 0

            if recommended_pitch_number:
                for i, pitch in enumerate(pitch_options):
                    if re.search(rf"(?i)^OPTION\s+{recommended_pitch_number}\b", pitch.strip()):
                        default_index = i
                        break

            if recommended_pitch_number:
                st.info(f"Recommended pitch detected: Option {recommended_pitch_number}. Auto-selecting it by default.")

            selected_pitch = st.selectbox(
                "Select the pitch you want to use",
                pitch_options,
                index=default_index,
                format_func=lambda x: x.split("\n")[0][:80],
                key="selected_pitch"
            )

            if selected_pitch:
                save_markdown(OUTPUTS_DIR / "01_selected_pitch.md", selected_pitch)

                st.success("Selected pitch auto-saved to outputs/01_selected_pitch.md")
                st.text_area("Selected Pitch Preview", selected_pitch, height=300)
        else:
            st.warning("Could not split options cleanly. Copy your chosen pitch manually.")


if page == "Step 2 - Ending Plotting":
    st.header("Step 2 - Ending Plotting")

    pitch_text = read_markdown(OUTPUTS_DIR / "01_selected_pitch.md")

    if not pitch_text.strip():
        st.error("No selected pitch found. Go to Step 1 and select a pitch first.")
    else:
        st.subheader("Selected Pitch")
        st.text_area("Selected pitch file content", pitch_text, height=250)

        if st.button("Generate Ending Options"):
            prompt = generate_endings_prompt(pitch_text)
            with st.spinner("Generating ending options..."):
                result = ask_openai(prompt, model=model)

            st.session_state["ending_options_raw"] = result
            st.session_state["ending_options"] = split_options(result, label="ENDING")

            recommended_ending_number = extract_recommended_number(
                result,
                recommendation_label="ENDING",
                item_label="ENDING"
            )
            st.session_state["recommended_ending_number"] = recommended_ending_number

        if "ending_options_raw" in st.session_state:
            st.subheader("Generated Ending Options")
            st.markdown(st.session_state["ending_options_raw"])

            ending_options = st.session_state.get("ending_options", [])

            if ending_options:
                recommended_ending_number = st.session_state.get("recommended_ending_number")

                default_index = 0

                if recommended_ending_number:
                    for i, ending in enumerate(ending_options):
                        if re.search(rf"(?i)^ENDING\s+{recommended_ending_number}\b", ending.strip()):
                            default_index = i
                            break

                if recommended_ending_number:
                    st.info(f"Recommended ending detected: Ending {recommended_ending_number}. Auto-selecting it by default.")

                selected_ending = st.selectbox(
                    "Select the ending you want to use",
                    ending_options,
                    index=default_index,
                    format_func=lambda x: x.split("\n")[0][:80],
                    key="selected_ending"
                )

                st.text_area("Selected Ending Preview", selected_ending, height=300)

                selected_ending_hash = hashlib.md5(selected_ending.encode("utf-8")).hexdigest()

                if st.session_state.get("expanded_ending_hash") != selected_ending_hash:
                    with st.spinner("Expanding and auto-saving selected ending..."):
                        expand_prompt = generate_expand_ending_prompt(pitch_text, selected_ending)
                        expanded_ending = ask_openai(expand_prompt, model=model)

                    save_markdown(OUTPUTS_DIR / "02_selected_ending.md", expanded_ending)

                    st.session_state["expanded_ending_hash"] = selected_ending_hash
                    st.session_state["expanded_ending_text"] = expanded_ending

                expanded_ending_text = st.session_state.get(
                    "expanded_ending_text",
                    read_markdown(OUTPUTS_DIR / "02_selected_ending.md")
                )

                st.success("Expanded ending auto-saved to outputs/02_selected_ending.md")
                st.subheader("Expanded Confirmed Ending")
                st.markdown(expanded_ending_text)
            else:
                st.warning("Could not split endings cleanly. Copy your chosen ending manually.")


if page == "Step 3 - Metadata":
    st.header("Step 3 - Metadata")

    pitch_text = read_markdown(OUTPUTS_DIR / "01_selected_pitch.md")
    ending_text = read_markdown(OUTPUTS_DIR / "02_selected_ending.md")

    if st.button("Generate Metadata"):
        if not pitch_text.strip() or not ending_text.strip():
            st.error("Generate Step 1 and Step 2 first.")
        else:
            prompt = generate_metadata_prompt(pitch_text, ending_text)
            with st.spinner("Generating metadata..."):
                result = ask_openai(prompt, model=model)

            save_markdown(OUTPUTS_DIR / "03_metadata.md", result)
            st.success("Saved to outputs/03_metadata.md")
            st.markdown(result)


if page == "Step 4 - Character Profiles":
    st.header("Step 4 - Character Profiles")

    metadata_text = read_markdown(OUTPUTS_DIR / "03_metadata.md")
    ending_text = read_markdown(OUTPUTS_DIR / "02_selected_ending.md")

    if st.button("Generate Character Profiles"):
        if not metadata_text.strip() or not ending_text.strip():
            st.error("Generate metadata and endings first.")
        else:
            prompt = generate_character_prompt(metadata_text, ending_text)
            with st.spinner("Generating character profiles..."):
                result = ask_openai(prompt, model=model)

            save_markdown(OUTPUTS_DIR / "04_characters.md", result)
            st.success("Saved to outputs/04_characters.md")
            st.markdown(result)


if page == "Step 5 - Outline":
    st.header("Step 5 - Outline")

    metadata_text = read_markdown(OUTPUTS_DIR / "03_metadata.md")
    character_text = read_markdown(OUTPUTS_DIR / "04_characters.md")
    ending_text = read_markdown(OUTPUTS_DIR / "02_selected_ending.md")

    if st.button("Generate Outline"):
        if not metadata_text.strip() or not character_text.strip() or not ending_text.strip():
            st.error("Generate metadata, character profiles, and endings first.")
        else:
            prompt = generate_outline_prompt(metadata_text, character_text, ending_text)
            with st.spinner("Generating outline..."):
                result = ask_openai(prompt, model=model)

            save_markdown(OUTPUTS_DIR / "05_outline.md", result)
            st.success("Saved to outputs/05_outline.md")
            st.markdown(result)


if page == "Step 6 - Write Chapter":
    st.header("Step 6 - Write Chapter")

    chapter_number = st.number_input("Chapter number", min_value=1, step=1)

    metadata_text = read_markdown(OUTPUTS_DIR / "03_metadata.md")
    character_text = read_markdown(OUTPUTS_DIR / "04_characters.md")
    ending_text = read_markdown(OUTPUTS_DIR / "02_selected_ending.md")
    outline_text = read_markdown(OUTPUTS_DIR / "05_outline.md")

    if st.button("Write Chapter"):
        if not metadata_text.strip() or not character_text.strip() or not ending_text.strip() or not outline_text.strip():
            st.error("Generate metadata, characters, ending, and outline first.")
        else:
            prompt = generate_chapter_prompt(
                chapter_number,
                metadata_text,
                character_text,
                ending_text,
                outline_text
            )

            with st.spinner(f"Writing Chapter {chapter_number}..."):
                result = ask_openai(prompt, model=model)

            file_name = f"chapter_{int(chapter_number):02}.md"
            save_markdown(CHAPTERS_DIR / file_name, result)

            st.success(f"Saved to chapters/{file_name}")
            st.markdown(result)