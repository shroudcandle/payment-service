from __future__ import annotations

import uuid

import pytest

from tests.fakes.item_entity import Item


def test_entities_with_same_id_are_equal() -> None:
    item_id = uuid.uuid4()

    assert Item(item_id) == Item(item_id)


def test_entities_with_different_ids_are_not_equal() -> None:
    assert Item(uuid.uuid4()) != Item(uuid.uuid4())


def test_entity_is_not_equal_to_other_types() -> None:
    item = Item(uuid.uuid4())

    assert item != object()
    assert item != "not-an-entity"


def test_entities_without_id_are_equal_only_by_identity() -> None:
    assert Item(None) != Item(None)
    item = Item(None)
    assert item == item


def test_entity_with_id_does_not_equal_entity_without_id() -> None:
    assert Item(None) != Item(uuid.uuid4())
    assert Item(uuid.uuid4()) != Item(None)


def test_entities_are_unhashable() -> None:
    with pytest.raises(TypeError):
        hash(Item(uuid.uuid4()))
