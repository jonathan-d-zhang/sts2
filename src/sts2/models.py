from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class MapPointType(StrEnum):
    MONSTER = "monster"
    ELITE = "elite"
    BOSS = "boss"
    REST_SITE = "rest_site"
    SHOP = "shop"
    TREASURE = "treasure"
    ANCIENT = "ancient"
    UNKNOWN = "unknown"


class RoomType(StrEnum):
    MONSTER = "monster"
    ELITE = "elite"
    BOSS = "boss"
    REST_SITE = "rest_site"
    SHOP = "shop"
    TREASURE = "treasure"
    EVENT = "event"


class Enchantment(BaseModel):
    id: str
    amount: int


class CardPropInt(BaseModel):
    name: str
    value: int


class CardProps(BaseModel):
    ints: list[CardPropInt] = Field(default_factory=list)


class Card(BaseModel):
    id: str
    floor_added_to_deck: int | None = None
    current_upgrade_level: int | None = None
    enchantment: Enchantment | None = None
    props: CardProps | None = None


class CardChoice(BaseModel):
    card: Card
    was_picked: bool


class CardEnchanted(BaseModel):
    card: Card
    enchantment: str


class CardTransformed(BaseModel):
    original_card: Card
    final_card: Card


class PotionChoice(BaseModel):
    choice: str
    was_picked: bool


class RelicChoice(BaseModel):
    choice: str
    was_picked: bool


class EventVariable(BaseModel):
    type: str
    decimal_value: float
    bool_value: bool
    string_value: str | None


class EventTitle(BaseModel):
    key: str
    table: str


class EventChoice(BaseModel):
    title: EventTitle
    variables: dict[str, EventVariable] = Field(default_factory=dict)


class AncientChoice(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text_key: str = Field(alias="TextKey")
    title: EventTitle
    was_chosen: bool


class Room(BaseModel):
    room_type: RoomType
    turns_taken: int
    model_id: str | None = None
    monster_ids: list[str] = Field(default_factory=list)


class _PlayerStatsBase(BaseModel):
    current_gold: int
    current_hp: int
    max_hp: int
    damage_taken: int
    gold_gained: int
    gold_lost: int
    gold_spent: int
    gold_stolen: int
    hp_healed: int
    max_hp_gained: int
    max_hp_lost: int
    ancient_choice: list[AncientChoice] | None = None
    bought_colorless: list[str] = Field(default_factory=list)
    bought_potions: list[str] = Field(default_factory=list)
    bought_relics: list[str] = Field(default_factory=list)
    card_choices: list[CardChoice] = Field(default_factory=list)
    cards_enchanted: list[CardEnchanted] = Field(default_factory=list)
    cards_gained: list[Card] = Field(default_factory=list)
    cards_removed: list[Card] = Field(default_factory=list)
    cards_transformed: list[CardTransformed] = Field(default_factory=list)
    completed_quests: list[str] = Field(default_factory=list)
    downgraded_cards: list[str] = Field(default_factory=list)
    event_choices: list[EventChoice] = Field(default_factory=list)
    potion_choices: list[PotionChoice] = Field(default_factory=list)
    potion_discarded: list[str] = Field(default_factory=list)
    potion_used: list[str] = Field(default_factory=list)
    relic_choices: list[RelicChoice] = Field(default_factory=list)
    relics_removed: list[str] = Field(default_factory=list)
    rest_site_choices: list[str] = Field(default_factory=list)
    upgraded_cards: list[str] = Field(default_factory=list)


class SinglePlayerStats(_PlayerStatsBase):
    player_id: Literal[1]


# Steam ID — a 64-bit integer, always > 1
SteamId = Annotated[int, Field(gt=1)]


class MultiPlayerStats(_PlayerStatsBase):
    player_id: SteamId


class SingleMapPoint(BaseModel):
    map_point_type: MapPointType
    rooms: list[Room]
    player_stats: list[SinglePlayerStats]


class MultiMapPoint(BaseModel):
    map_point_type: MapPointType
    rooms: list[Room]
    player_stats: list[MultiPlayerStats]


class Modifier(BaseModel):
    id: str


class Potion(BaseModel):
    id: str
    slot_index: int


class Relic(BaseModel):
    id: str
    floor_added_to_deck: int


class _PlayerBase(BaseModel):
    character: str
    deck: list[Card]
    relics: list[Relic]
    potions: list[Potion]
    max_potion_slot_count: int


class SinglePlayer(_PlayerBase):
    id: Literal[1]


class MultiPlayer(_PlayerBase):
    id: SteamId


class _RunBase(BaseModel):
    acts: list[str]
    ascension: int
    build_id: str
    game_mode: str
    killed_by_encounter: str
    killed_by_event: str
    modifiers: list[Modifier]
    platform_type: str
    run_time: int
    schema_version: int
    seed: str
    start_time: int
    was_abandoned: bool
    win: bool


class SinglePlayerRun(_RunBase):
    players: list[SinglePlayer]
    map_point_history: list[list[SingleMapPoint]]


class MultiPlayerRun(_RunBase):
    players: list[MultiPlayer]
    map_point_history: list[list[MultiMapPoint]]


Run = SinglePlayerRun | MultiPlayerRun