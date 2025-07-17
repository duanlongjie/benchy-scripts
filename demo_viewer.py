import os
import numpy as np
import polars as pl
import streamlit as st
from st_diff_viewer import diff_viewer
from streamlit_scroll_navigation import scroll_navbar

st.set_page_config(layout="wide", page_title="Demo Viewer", page_icon=":robot:")


def process_chunks(text: str):
    import re

    i = 0
    while i < len(text):
        # Check for <think> tag
        think_match = re.search(r"<think>(.*?)</think>", text[i:], re.DOTALL)
        func_match = re.search(
            r"<function=([^>]+)>(.*?)</function>", text[i:], re.DOTALL
        )
        current_match = re.search(
            r"\[Current working directory: (.*?)\]\s*\[Execution time: (.*?)\]\s*\[Command finished with exit code (.*?)\]",
            text[i:],
            re.DOTALL,
        )

        # Find the earliest match
        think_start = think_match.start() + i if think_match else len(text)
        func_start = func_match.start() + i if func_match else len(text)
        current_start = current_match.start() + i if current_match else len(text)

        # Process regular text before any tags
        next_tag_start = min(think_start, func_start, current_start)
        if next_tag_start > i:
            regular_text = text[i:next_tag_start].strip()
            if regular_text:
                st.text(regular_text)
            i = next_tag_start
            continue

        # Process <think> tag
        if think_start < func_start and think_match:
            think_content = think_match.group(1).strip()
            if think_content:
                st.info(f"**THINKING**:\n\n{think_content}")
            i = think_start + len(think_match.group(0))
            continue

        # Process <function> tag
        if func_start <= think_start and func_match:
            function_name = func_match.group(1)
            function_content = func_match.group(2)

            st.info(f"**CALLING FUNCTION**: {function_name}")

            # Process content within function, looking for parameter tags
            process_function_content(function_content)

            i = func_start + len(func_match.group(0))
            continue

            # Process [Current] tag
        if current_start < min(think_start, func_start) and current_match:
            working_dir = current_match.group(1).strip()
            execution_time = current_match.group(2).strip()
            exit_code = current_match.group(3).strip()

            # Format the block with preserved newlines
            st.table(
                {
                    "Working Directory": working_dir,
                    "Execution Time": execution_time,
                    "Exit Code": exit_code,
                }
            )

            i = current_start + len(current_match.group(0))
            continue

        # If no matches found, we're done
        break


def process_all_parameters(all_params: dict):
    if "old_str" in all_params:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**old_str**")
            st.code(all_params["old_str"])
        with col2:
            st.markdown("**new_str**")
            st.code(all_params["new_str"])
        # diff_viewer(all_params["old_str"], all_params["new_str"], split_view=True)

    for param_name, param_content in all_params.items():
        if param_name != "old_str" and param_name != "new_str":
            process_parameters(param_name, param_content)


def process_parameters(name: str, content: str):
    st.markdown(f"**{name}**")
    if content:
        st.code(content)


def process_function_content(content: str):
    import re

    i = 0
    all_params = {}
    while i < len(content):
        # Look for <parameter= tags
        param_match = re.search(
            r"<parameter=([^>]+)>(.*?)</parameter>", content[i:], re.DOTALL
        )

        if param_match:
            param_start = param_match.start() + i

            # Process regular text before parameter
            if param_start > i:
                regular_text = content[i:param_start].strip()
                if regular_text:
                    st.code(regular_text)

            # Process parameter
            param_name = param_match.group(1)
            param_content = param_match.group(2).strip()

            all_params[param_name] = param_content

            i = param_start + len(param_match.group(0))
        else:
            # No more parameters, process remaining content
            remaining_content = content[i:].strip()
            if remaining_content:
                st.code(remaining_content)
            break

    process_all_parameters(all_params)


evaluation_file = st.file_uploader(
    "Upload demo file", type=["json", "txt"], accept_multiple_files=False
)
num_rows = 0

if evaluation_file:
    df_demo = pl.read_json(evaluation_file)

    for idx, row in enumerate(df_demo.iter_rows(named=True)):
        st.header(f"Step {idx}", anchor=f"step_{idx}")
        st.subheader(f"{row['role']}:")
        process_chunks(row["content"])
        st.divider()

    with st.sidebar:
        st.subheader("Navigation")
        scroll_navbar(
            key="main",
            anchor_ids=[f"step_{i}" for i in range(len(df_demo))],
        )
