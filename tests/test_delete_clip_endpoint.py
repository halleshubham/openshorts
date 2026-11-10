"""DELETE /api/clip/{job_id}/{clip_index}: removes every rendered version of a
clip and leaves a tombstone, so the other clips keep their index."""

import asyncio
import json

import httpx
import pytest

app_module = pytest.importorskip("app")

JOB_ID = "delete-clip-test-job"


def _request(method, path):
    async def _do():
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport,
                                     base_url="http://testserver") as client:
            return await client.request(method, path)
    return asyncio.run(_do())


@pytest.fixture()
def job(tmp_path, monkeypatch):
    out_root = tmp_path / "output"
    job_dir = out_root / JOB_ID
    job_dir.mkdir(parents=True)
    monkeypatch.setattr(app_module, "OUTPUT_DIR", str(out_root))

    clips = [
        {"video_title_for_youtube_short": "one", "video_url": f"/videos/{JOB_ID}/t_clip_1.mp4"},
        {"video_title_for_youtube_short": "two", "video_url": f"/videos/{JOB_ID}/t_clip_2.mp4"},
    ]
    (job_dir / "t_metadata.json").write_text(json.dumps({"shorts": clips}))
    for name in ("t_clip_1.mp4", "subtitled_1_t_clip_1.mp4", "hooked_2_t_clip_1.mp4",
                 "t_clip_1.mp4.layout.json", "t_clip_2.mp4", "subtitled_1_t_clip_2.mp4",
                 "t_clip_11.mp4"):
        (job_dir / name).write_bytes(b"x")

    app_module.jobs[JOB_ID] = {
        "status": "completed", "logs": [],
        "result": {"clips": [dict(c) for c in clips]},
        "user_id": None, "watermark": False,
    }
    try:
        yield job_dir
    finally:
        app_module.jobs.pop(JOB_ID, None)


def test_deletes_every_version_and_keeps_other_clips(job):
    resp = _request("DELETE", f"/api/clip/{JOB_ID}/0")
    assert resp.status_code == 200
    left = sorted(p.name for p in job.iterdir())
    # Clip 1's canonical, subtitled, hooked and sidecar are gone; clip 2 and
    # the look-alike name t_clip_11.mp4 are untouched.
    assert left == ["subtitled_1_t_clip_2.mp4", "t_clip_11.mp4", "t_clip_2.mp4", "t_metadata.json"]


def test_marks_a_tombstone_instead_of_shifting_indices(job):
    _request("DELETE", f"/api/clip/{JOB_ID}/0")
    shorts = json.loads((job / "t_metadata.json").read_text())["shorts"]
    assert [c.get("deleted", False) for c in shorts] == [True, False]
    assert shorts[1]["video_title_for_youtube_short"] == "two"
    mem = app_module.jobs[JOB_ID]["result"]["clips"]
    assert mem[0]["deleted"] is True and "deleted" not in mem[1]


def test_unknown_job_and_index_are_404(job):
    assert _request("DELETE", "/api/clip/no-such-job/0").status_code == 404
    assert _request("DELETE", f"/api/clip/{JOB_ID}/9").status_code == 404
    assert _request("DELETE", f"/api/clip/{JOB_ID}/-1").status_code == 404
