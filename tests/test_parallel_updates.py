"""Tests for PARALLEL_UPDATES constant on all platforms (Issue #296).

These tests verify that all entity platforms define PARALLEL_UPDATES
to comply with Home Assistant Integration Quality Scale Silver tier.
"""

from __future__ import annotations


class TestPlatformParallelUpdates:
    """Tests for PARALLEL_UPDATES on all platform modules."""

    def test_media_player_has_parallel_updates(self) -> None:
        """Test that media_player.py has PARALLEL_UPDATES defined."""
        from custom_components.embymedia import media_player

        assert hasattr(media_player, "PARALLEL_UPDATES")
        # media_player has service actions, so should be limited
        assert media_player.PARALLEL_UPDATES == 1

    def test_sensor_has_parallel_updates(self) -> None:
        """Test that sensor.py has PARALLEL_UPDATES defined."""
        from custom_components.embymedia import sensor

        assert hasattr(sensor, "PARALLEL_UPDATES")
        # sensor is read-only, coordinator handles updates
        assert sensor.PARALLEL_UPDATES == 0

    def test_binary_sensor_has_parallel_updates(self) -> None:
        """Test that binary_sensor.py has PARALLEL_UPDATES defined."""
        from custom_components.embymedia import binary_sensor

        assert hasattr(binary_sensor, "PARALLEL_UPDATES")
        # binary_sensor is read-only, coordinator handles updates
        assert binary_sensor.PARALLEL_UPDATES == 0

    def test_button_has_parallel_updates(self) -> None:
        """Test that button.py has PARALLEL_UPDATES defined."""
        from custom_components.embymedia import button

        assert hasattr(button, "PARALLEL_UPDATES")
        # button has press action, should be limited
        assert button.PARALLEL_UPDATES == 1

    def test_remote_has_parallel_updates(self) -> None:
        """Test that remote.py has PARALLEL_UPDATES defined."""
        from custom_components.embymedia import remote

        assert hasattr(remote, "PARALLEL_UPDATES")
        # remote has navigation commands, should be limited
        assert remote.PARALLEL_UPDATES == 1

    def test_image_has_parallel_updates(self) -> None:
        """Test that image.py has PARALLEL_UPDATES defined."""
        from custom_components.embymedia import image

        assert hasattr(image, "PARALLEL_UPDATES")
        # image is read-only, coordinator handles updates
        assert image.PARALLEL_UPDATES == 0

    def test_notify_has_parallel_updates(self) -> None:
        """Test that notify.py has PARALLEL_UPDATES defined."""
        from custom_components.embymedia import notify

        assert hasattr(notify, "PARALLEL_UPDATES")
        # notify has send message action, should be limited
        assert notify.PARALLEL_UPDATES == 1
