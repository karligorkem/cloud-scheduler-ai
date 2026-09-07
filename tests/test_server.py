import pytest

from cloud_scheduler.domain.server import Server


def test_server_starts_with_all_resources_available() -> None:
    server = Server(
        server_id="server-1",
        total_cpu=16,
        total_memory_gb=32.0,
        gpu_count=2,
    )

    assert server.server_id == "server-1"
    assert server.total_cpu == 16
    assert server.available_cpu == 16
    assert server.total_memory_gb == 32.0
    assert server.available_memory_gb == 32.0
    assert server.gpu_count == 2
    assert server.available_gpu_count == 2
    assert server.is_active is True


def test_server_uses_zero_gpu_by_default() -> None:
    server = Server(
        server_id="server-cpu-1",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    assert server.gpu_count == 0
    assert server.available_gpu_count == 0


def test_server_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match="Server ID cannot be empty"):
        Server(
            server_id="   ",
            total_cpu=16,
            total_memory_gb=32.0,
        )


def test_server_rejects_zero_cpu() -> None:
    with pytest.raises(ValueError, match="Total CPU must be greater than zero"):
        Server(
            server_id="server-1",
            total_cpu=0,
            total_memory_gb=32.0,
        )


def test_server_rejects_negative_memory() -> None:
    with pytest.raises(ValueError, match="Total memory must be greater than zero"):
        Server(
            server_id="server-1",
            total_cpu=16,
            total_memory_gb=-4.0,
        )


def test_server_rejects_negative_gpu_count() -> None:
    with pytest.raises(ValueError, match="GPU count cannot be negative"):
        Server(
            server_id="server-1",
            total_cpu=16,
            total_memory_gb=32.0,
            gpu_count=-1,
        )


def test_server_removes_spaces_from_id() -> None:
    server = Server(
        server_id="  server-1  ",
        total_cpu=16,
        total_memory_gb=32.0,
    )

    assert server.server_id == "server-1"