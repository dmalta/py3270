from __future__ import annotations

from unittest.mock import MagicMock

from ibm3270 import SessionManager, Terminal


def test_create_get_list_close_session() -> None:
    manager = SessionManager()
    session_id = manager.create_session()

    assert session_id in manager.list_sessions()
    session = manager.get_session(session_id)
    assert isinstance(session, Terminal)

    session.stop = MagicMock()  # type: ignore[method-assign]
    manager.close_session(session_id)

    session.stop.assert_called_once()
    assert session_id not in manager.list_sessions()


def test_close_all() -> None:
    manager = SessionManager()
    id1 = manager.create_session()
    id2 = manager.create_session()

    s1 = manager.get_session(id1)
    s2 = manager.get_session(id2)
    s1.stop = MagicMock()  # type: ignore[method-assign]
    s2.stop = MagicMock()  # type: ignore[method-assign]

    manager.close_all()

    s1.stop.assert_called_once()
    s2.stop.assert_called_once()
    assert manager.list_sessions() == []
