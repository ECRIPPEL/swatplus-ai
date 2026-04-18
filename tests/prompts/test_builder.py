"""Tests for :mod:`swatplus_ai.prompts.builder`."""

from __future__ import annotations

import re
from pathlib import Path

from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.llm.interface import Message
from swatplus_ai.parser.txtinout import TxtInOutProject
from swatplus_ai.prompts.builder import (
    ProjectSummary,
    StaticPassage,
    build_module1_prompt,
)


def test_returns_two_messages_system_then_user(
    summary: ProjectSummary,
    error_a: Finding,
) -> None:
    messages = build_module1_prompt([error_a], summary)
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert all(isinstance(m, Message) for m in messages)


def test_all_placeholders_substituted(
    summary: ProjectSummary,
    error_a: Finding,
    passage_a: StaticPassage,
) -> None:
    messages = build_module1_prompt([error_a], summary, [passage_a])
    system = messages[0].content
    # No {{VAR}} survives rendering.
    assert not re.search(r"\{\{[A-Z_]+\}\}", system)


def test_findings_errors_before_warnings(
    summary: ProjectSummary,
    error_a: Finding,
    error_b: Finding,
    warning_a: Finding,
) -> None:
    # Pass findings in an order that forces the builder to re-group.
    messages = build_module1_prompt([warning_a, error_b, error_a], summary)
    body = messages[0].content
    first_warning = body.index("### warning:")
    for err_id in (error_a.id, error_b.id):
        assert body.index(f"### error: {err_id}") < first_warning


def test_same_severity_sorted_by_id(
    summary: ProjectSummary,
    error_a: Finding,
    error_b: Finding,
) -> None:
    # error_a.id = "setup.files_present", error_b.id = "chan.routing_topology".
    # Expect chan.* before setup.* regardless of input order.
    messages = build_module1_prompt([error_a, error_b], summary)
    body = messages[0].content
    assert body.index(f"### error: {error_b.id}") < body.index(f"### error: {error_a.id}")


def test_static_passages_none_renders_literal(
    summary: ProjectSummary,
    error_a: Finding,
) -> None:
    messages = build_module1_prompt([error_a], summary, None)
    assert "None provided." in messages[0].content


def test_static_passages_empty_list_renders_literal(
    summary: ProjectSummary,
    error_a: Finding,
) -> None:
    messages = build_module1_prompt([error_a], summary, [])
    assert "None provided." in messages[0].content


def test_static_passages_two_blocks_in_order(
    summary: ProjectSummary,
    error_a: Finding,
    passage_a: StaticPassage,
    passage_b: StaticPassage,
) -> None:
    messages = build_module1_prompt([error_a], summary, [passage_a, passage_b])
    body = messages[0].content
    idx_a = body.index(f"## [{passage_a.id}] {passage_a.title}")
    idx_b = body.index(f"## [{passage_b.id}] {passage_b.title}")
    assert idx_a < idx_b
    assert passage_a.body in body
    assert passage_b.body in body
    assert f"source: {passage_a.source}" in body
    assert f"source: {passage_b.source}" in body


def test_project_summary_from_project_extracts_fields(minimal_project_path: Path) -> None:
    project = TxtInOutProject.read(minimal_project_path)
    s = ProjectSummary.from_project(project)
    assert s.sim_start_year == project.time_sim.yrc_start
    assert s.sim_end_year == project.time_sim.yrc_end
    assert s.warmup_years == project.print_prt.nyskip
    assert s.pet_method == project.codes_bsn.pet
    # The minimal fixture ships object.cnt, so count fields are populated.
    assert project.object_cnt is not None
    assert s.n_hrus == project.object_cnt.hru
    assert s.n_channels == project.object_cnt.cha
    assert s.n_aquifers == project.object_cnt.aqu
    assert s.n_subbasins == project.object_cnt.rtu
    assert s.basin_area_km2 == project.object_cnt.tot_area


def test_project_summary_tolerates_missing_object_cnt(minimal_project_path: Path) -> None:
    project = TxtInOutProject.read(minimal_project_path)
    trimmed = project.model_copy(update={"object_cnt": None})
    s = ProjectSummary.from_project(trimmed)
    # Required fields still populated.
    assert s.sim_start_year == project.time_sim.yrc_start
    assert s.warmup_years == project.print_prt.nyskip
    assert s.pet_method == project.codes_bsn.pet
    # Counts degrade to None instead of raising.
    assert s.n_hrus is None
    assert s.n_channels is None
    assert s.n_aquifers is None
    assert s.n_subbasins is None
    assert s.basin_area_km2 is None


def test_template_contains_never_invent_guardrail(
    summary: ProjectSummary,
    error_a: Finding,
) -> None:
    messages = build_module1_prompt([error_a], summary)
    # The "never invent" ground rule must survive into the rendered prompt —
    # the template is data, so pinning its critical phrasing is fair game.
    assert "never invent" in messages[0].content.lower()


def test_user_message_mentions_diagnostic_report(
    summary: ProjectSummary,
    error_a: Finding,
) -> None:
    messages = build_module1_prompt([error_a], summary)
    user_content = messages[1].content.lower()
    assert "diagnostic" in user_content or "report" in user_content


def test_finding_without_references_renders_dash(
    summary: ProjectSummary,
    error_b: Finding,
) -> None:
    # error_b has references=() by construction.
    messages = build_module1_prompt([error_b], summary)
    body = messages[0].content
    # The block for this finding ends with "references: —", never an empty
    # string — otherwise the LLM sees a dangling label with no value.
    assert "references: —" in body
    assert "references: \n" not in body
    assert "references: ," not in body
