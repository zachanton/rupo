# -*- coding: utf-8 -*-
# Автор: Гусев Илья
# Описание: Класс для удобной работы со словарём ударений.

import datrie
import os
from typing import List, Tuple
from enum import Enum

from rupo.util.cmu import CMUDict
from rupo.util.zaliznyak import ZalyzniakDict
from rupo.settings import RU_GRAPHEME_ACCENT_PATH, RU_GRAPHEME_ACCENT_TRIE_PATH, \
    EN_PHONEME_ACCENT_PATH, EN_PHONEME_ACCENT_TRIE_PATH, \
    RU_PHONEME_ACCENT_PATH, RU_PHONEME_ACCENT_TRIE_PATH, RU_GRAPHEME_SET, PHONEME_SET


class StressDict:
    """
    Класс данных, для сериализации словаря как префиксного дерева и быстрой загрузки в память.
    """

    class Language:
        ENGLISH = 0
        RUSSIAN = 1

    class Mode:
        GRAPHEMES = 0
        PHONEMES = 0

    class StressType(Enum):
        ANY = -1
        PRIMARY = 0
        SECONDARY = 1

    def __init__(self, language: Language=Language.RUSSIAN, mode: Mode=Mode.GRAPHEMES) -> None:
        if language == self.Language.RUSSIAN and mode == self.Mode.GRAPHEMES:
            self.data = datrie.Trie(RU_GRAPHEME_SET)
            src_filename = RU_GRAPHEME_ACCENT_PATH
            if not os.path.exists(RU_GRAPHEME_ACCENT_PATH):
                ZalyzniakDict.convert_to_accent_only(RU_GRAPHEME_ACCENT_PATH)
            dst_filename = RU_GRAPHEME_ACCENT_TRIE_PATH
        elif mode == self.Mode.PHONEMES and language == self.Language.ENGLISH:
            self.data = datrie.Trie(PHONEME_SET)
            src_filename = EN_PHONEME_ACCENT_PATH
            if not os.path.exists(EN_PHONEME_ACCENT_PATH):
                CMUDict.convert_to_phoneme_accent(EN_PHONEME_ACCENT_PATH)
            dst_filename = EN_PHONEME_ACCENT_TRIE_PATH
        elif mode == self.Mode.PHONEMES and language == self.Language.RUSSIAN:
            self.data = datrie.Trie(PHONEME_SET)
            src_filename = RU_PHONEME_ACCENT_PATH
            if not os.path.exists(RU_PHONEME_ACCENT_PATH):
                ZalyzniakDict.convert_to_phoneme_accent(RU_PHONEME_ACCENT_PATH)
            dst_filename = RU_PHONEME_ACCENT_TRIE_PATH
        else:
            assert False
        if not os.path.isfile(src_filename):
            raise FileNotFoundError("Не найден файл словаря.")
        if os.path.isfile(dst_filename):
            self.data = datrie.Trie.load(dst_filename)
        else:
            self.create(src_filename, dst_filename)

    def create(self, src_filename: str, dst_filename: str) -> None:
        """
        Загрузка словаря из файла.

        :param src_filename: имя файла с оригинальным словарём.
        :param dst_filename: имя файла, в который будет сохранён дамп.
        """
        with open(src_filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                word, primary, secondary = line.split("\t")
                stresses = [(int(a), StressDict.StressType.PRIMARY) for a in primary.strip().split(",")]
                if secondary.strip() != "":
                    stresses += [(int(a), StressDict.StressType.SECONDARY) for a in secondary.strip().split(",")]
                self.update(word, stresses)
        self.data.save(dst_filename)

    def save(self, dst_filename: str) -> None:
        """
        Сохранение дампа.

        :param dst_filename: имя файла, в который сохраняем дамп словаря.
        """
        self.data.save(dst_filename)

    def get_stresses(self, word: str, stress_type: StressType=StressType.ANY) -> List[int]:
        """
        Получение ударений нужного типа у слова.

        :param word: слово, которое мы хотим посмотреть в словаре.
        :param stress_type: тип ударения.
        :return forms: массив всех ударений.
        """
        if word in self.data:
            if stress_type == StressDict.StressType.ANY:
                return [i[0] for i in self.data[word]]
            else:
                return [i[0] for i in self.data[word] if i[1] == stress_type]
        return []

    def get_all(self) -> List[Tuple[str, List[Tuple[int, StressType]]]]:
        """
        :return items: все ключи и ударения словаря.
        """
        return self.data.items()

    def update(self, word: str, stress_pairs: List[Tuple[int, StressType]]) -> None:
        """
        Обновление словаря.

        :param word: слово.
        :param stress_pairs: набор ударений.
        """
        if word not in self.data:
            self.data[word] = set(stress_pairs)
        else:
            self.data[word].update(stress_pairs)