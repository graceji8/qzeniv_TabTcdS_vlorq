"""Unit tests for dub_translate — no network, pure helpers + monkeypatched translator."""
import asyncio
import pytest


def test_translate_codes_cover_popular_iso():
    from api.routers.dub_translate import TRANSLATE_CODES
    popular = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi']
    for code in popular:
        assert code in TRANSLATE_CODES, f"{code} missing from TRANSLATE_CODES"


def test_flores_codes_cover_core_languages():
    from api.routers.dub_translate import FLORES_CODES
    for code in ('en', 'de', 'es', 'fr', 'hi', 'ja'):
        assert code in FLORES_CODES


def test_resolve_source_lang_priority(monkeypatch):
    from api.routers import dub_translate

    class Req:
        def __init__(self, src=None, jid=None):
            self.source_lang = src
            self.job_id = jid

    # Explicit source_lang wins
    assert dub_translate._resolve_source_lang(Req(src='fr')) == 'fr'

    # Fall through to job-detected source_lang
    monkeypatch.setattr(
        dub_translate, '_get_job',
        lambda jid: {'source_lang': 'de'} if jid == 'j1' else None,
    )
    assert dub_translate._resolve_source_lang(Req(jid='j1')) == 'de'

    # No job, no explicit → default en
    assert dub_translate._resolve_source_lang(Req()) == 'en'
    assert dub_translate._resolve_source_lang(Req(jid='missing')) == 'en'


class _FakeSeg:
    def __init__(self, sid, text, target_lang=None):
        self.id = sid
        self.text = text
        self.target_lang = target_lang


class _FakeReq:
    def __init__(self, segments, target_lang, provider='google', source_lang=None):
        self.segments = segments
        self.target_lang = target_lang
        self.provider = provider
        self.source_lang = source_lang
        self.job_id = None


@pytest.mark.asyncio
async def test_google_path_passes_correct_target_code(monkeypatch):
    """GoogleTranslator constructed with the expected src/tgt codes for German."""
    from api.routers import dub_translate

    calls = []

    class FakeTranslator:
        def __init__(self, source=None, target=None, **kwargs):
            calls.append({'source': source, 'target': target})
        def translate(self, text):
            return f"[{calls[-1]['target']}]{text}"

    class FakeModule:
        GoogleTranslator = FakeTranslator
        DeepL = FakeTranslator
        MyMemoryTranslator = FakeTranslator
        MicrosoftTranslator = FakeTranslator

    monkeypatch.setitem(__import__('sys').modules, 'deep_translator', FakeModule)

    req = _FakeReq(
        segments=[_FakeSeg('s1', 'Hello'), _FakeSeg('s2', 'World')],
        target_lang='de',
        provider='google',
        source_lang='en',
    )
    resp = await dub_translate.dub_translate(req)
    assert resp['target_lang'] == 'de'
    assert resp['source_lang'] == 'en'
    texts = {t['id']: t['text'] for t in resp['translated']}
    assert texts['s1'] == '[de]Hello'
    assert texts['s2'] == '[de]World'
    # Each segment built a translator with de as target
    assert all(c['target'] == 'de' for c in calls)
    # Source came through as "en"
    assert any(c['source'] == 'en' for c in calls)


@pytest.mark.asyncio
async def test_google_path_uses_seg_target_lang_override(monkeypatch):
    from api.routers import dub_translate

    class FakeTranslator:
        def __init__(self, source=None, target=None, **kwargs):
            self.target = target
        def translate(self, text):
            return f"[{self.target}]{text}"

    class FakeModule:
        GoogleTranslator = FakeTranslator

    monkeypatch.setitem(__import__('sys').modules, 'deep_translator', FakeModule)

    req = _FakeReq(
        segments=[
            _FakeSeg('s1', 'Hi', target_lang='bn'),  # per-segment override
            _FakeSeg('s2', 'Ok'),
        ],
        target_lang='de',
        provider='google',
        source_lang='en',
    )
    resp = await dub_translate.dub_translate(req)
    texts = {t['id']: t['text'] for t in resp['translated']}
    assert texts['s1'] == '[bn]Hi'
    assert texts['s2'] == '[de]Ok'


@pytest.mark.asyncio
async def test_google_retries_then_falls_back_to_auto(monkeypatch):
    """Transient failure → retry → still fails → fall back to auto source."""
    from api.routers import dub_translate

    attempts = []

    class FakeTranslator:
        def __init__(self, source=None, target=None, **kwargs):
            self.source = source
            self.target = target
        def translate(self, text):
            attempts.append(self.source)
            if self.source != 'auto':
                raise RuntimeError('transient google error')
            return f"[auto:{self.target}]{text}"

    class FakeModule:
        GoogleTranslator = FakeTranslator

    monkeypatch.setitem(__import__('sys').modules, 'deep_translator', FakeModule)

    req = _FakeReq(
        segments=[_FakeSeg('s1', 'Hello')],
        target_lang='de', provider='google', source_lang='en',
    )
    resp = await dub_translate.dub_translate(req)
    assert resp['translated'][0]['text'] == '[auto:de]Hello'
    assert 'error' not in resp['translated'][0]
    # explicit src tried at least once before auto
    assert attempts[0] == 'en'
    assert attempts[-1] == 'auto'


@pytest.mark.asyncio
async def test_google_reports_error_when_all_attempts_fail(monkeypatch):
    from api.routers import dub_translate

    class FakeTranslator:
        def __init__(self, **kwargs): pass
        def translate(self, text): raise RuntimeError('total failure')

    class FakeModule:
        GoogleTranslator = FakeTranslator

    monkeypatch.setitem(__import__('sys').modules, 'deep_translator', FakeModule)

    req = _FakeReq(
        segments=[_FakeSeg('s1', 'Hello')],
        target_lang='de', provider='google', source_lang='en',
    )
    resp = await dub_translate.dub_translate(req)
    seg = resp['translated'][0]
    assert seg['text'] == 'Hello', 'original text preserved on failure'
    assert 'error' in seg
    assert 'total failure' in seg['error']


@pytest.mark.asyncio
async def test_empty_text_skipped(monkeypatch):
    from api.routers import dub_translate

    class FakeTranslator:
        def __init__(self, **kwargs): pass
        def translate(self, text): return '[xx]' + text

    class FakeModule:
        GoogleTranslator = FakeTranslator

    monkeypatch.setitem(__import__('sys').modules, 'deep_translator', FakeModule)

    req = _FakeReq(
        segments=[_FakeSeg('s1', '  '), _FakeSeg('s2', 'hi')],
        target_lang='de', provider='google', source_lang='en',
    )
    resp = await dub_translate.dub_translate(req)
    texts = {t['id']: t['text'] for t in resp['translated']}
    assert texts['s1'].strip() == ''  # untouched
    assert texts['s2'] == '[xx]hi'


@pytest.mark.asyncio
async def test_empty_translation_preserves_original(monkeypatch):
    from api.routers import dub_translate

    class FakeTranslator:
        def __init__(self, **kwargs): pass
        def translate(self, text): return ''  # always empty

    class FakeModule:
        GoogleTranslator = FakeTranslator

    monkeypatch.setitem(__import__('sys').modules, 'deep_translator', FakeModule)

    req = _FakeReq(
        segments=[_FakeSeg('s1', 'hi')],
        target_lang='de', provider='google', source_lang='en',
    )
    resp = await dub_translate.dub_translate(req)
    seg = resp['translated'][0]
    assert seg['text'] == 'hi'
    assert 'error' in seg
