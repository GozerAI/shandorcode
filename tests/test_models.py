"""Core data model construction and serialization."""
from src.visualization.core.models import (
    CodeEntity,
    Dependency,
    DependencyType,
    EntityType,
    LanguageType,
    ShandorCode,
)


def test_shandorcode_to_dict_roundtrip() -> None:
    graph = ShandorCode(root_path="/tmp/x")
    entity = CodeEntity(
        id="file:foo.py",
        name="foo.py",
        type=EntityType.FILE,
        language=LanguageType.PYTHON,
        path="foo.py",
        start_line=1,
        end_line=10,
    )
    graph.add_entity(entity)
    graph.add_dependency(
        Dependency(
            source_id=entity.id,
            target_id="external:json",
            type=DependencyType.IMPORT,
        )
    )

    payload = graph.to_dict()
    assert "entities" in payload
    assert "dependencies" in payload
    assert payload["root_path"] == "/tmp/x"
    assert entity.id in payload["entities"]
    assert payload["language_breakdown"]["python"] == 1


def test_add_entity_updates_language_breakdown() -> None:
    graph = ShandorCode(root_path="/tmp/x")
    for lang in (LanguageType.PYTHON, LanguageType.PYTHON, LanguageType.JAVASCRIPT):
        graph.add_entity(
            CodeEntity(
                id=f"file:{lang.value}-{len(graph.entities)}.x",
                name="x",
                type=EntityType.FILE,
                language=lang,
                path="x",
                start_line=1,
                end_line=1,
            )
        )
    assert graph.language_breakdown[LanguageType.PYTHON] == 2
    assert graph.language_breakdown[LanguageType.JAVASCRIPT] == 1


def test_get_dependencies_for_and_dependents_of() -> None:
    graph = ShandorCode(root_path="/tmp/x")
    a = "file:a"
    b = "file:b"
    c = "file:c"
    graph.add_dependency(Dependency(source_id=a, target_id=b, type=DependencyType.IMPORT))
    graph.add_dependency(Dependency(source_id=a, target_id=c, type=DependencyType.IMPORT))
    graph.add_dependency(Dependency(source_id=c, target_id=b, type=DependencyType.CALL))

    assert {d.target_id for d in graph.get_dependencies_for(a)} == {b, c}
    assert {d.source_id for d in graph.get_dependents_of(b)} == {a, c}
