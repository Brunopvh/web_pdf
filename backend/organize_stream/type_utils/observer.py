#!/usr/bin/env python3
from __future__ import annotations
from abc import ABC, abstractmethod
from sheet_stream import TableDocuments


# Sujeito notificador
class NotifyProvider(ABC):

    def __init__(self):
        self._observers: list = []

    @property
    def observers(self) -> list:
        return self._observers

    @observers.setter
    def observers(self, value: list) -> None:
        pass

    @abstractmethod
    def add_observer(self, observer) -> None:
        pass

    @abstractmethod
    def send_notify(self, notify) -> None:
        pass


class NotifyTableExtract(NotifyProvider):

    def __init__(self):
        super().__init__()

    def add_observer(self, observer) -> None:
        if not isinstance(observer, ObserverTableExtraction):
            print(f'{__class__.__name__} Observador inválido')
            return
        self._observers.append(observer)

    def send_notify(self, notify) -> None:
        print(f'{__class__.__name__} Notificado!')
        observer: ObserverTableExtraction
        for observer in self._observers:
            observer.receive_notify(notify)


# Sujeito Observador.
class Observer(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def receive_notify(self, notify) -> None:
        pass


class ObserverTableExtraction(Observer):
    def __init__(self):
        super().__init__()

    def receive_notify(self, notify: TableDocuments) -> None:
        pass

