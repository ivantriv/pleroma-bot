import os
import shutil
import logging
import sys
from unittest.mock import patch
import pytest
import requests

from pleroma_bot import cli, User
from pleroma_bot._utils import random_string

from test_user import UserTemplate
from conftest import get_config_users


def test_unpin_pleroma_logger(sample_users, mock_request, caplog):
    with caplog.at_level(logging.WARNING):
        test_user = UserTemplate()

        for sample_user in sample_users:
            with sample_user['mock'] as mock:
                sample_user_obj = sample_user['user_obj']
                url_statuses = (
                    f"{test_user.pleroma_base_url}"
                    f"/api/v1/accounts/"
                    f"{sample_user_obj.pleroma_username}/statuses"
                )
                mock.get(
                    url_statuses,
                    json=mock_request['sample_data']['pleroma_statuses_pin'],
                    status_code=200
                )
                empty_file = os.path.join(os.getcwd(), 'empty.txt')
                open(empty_file, 'a').close()
                for t_user in sample_user_obj.twitter_username:
                    pinned_file = os.path.join(
                        sample_user_obj.user_path[t_user],
                        "pinned_id_pleroma.txt"
                    )
                    shutil.copy(empty_file, pinned_file)
                    sample_user_obj.unpin_pleroma(pinned_file)
                    os.remove(pinned_file)
                    os.remove(empty_file)
    assert 'Pinned post not found. Giving up unpinning...' in caplog.text


def test_main_exception_logger(global_mock, sample_users, caplog):
    with caplog.at_level(logging.ERROR):
        with global_mock as mock:
            prev_config = os.path.join(os.getcwd(), 'config.yml')
            backup_config = os.path.join(os.getcwd(), 'config.yml.bak')
            if os.path.isfile(prev_config):
                shutil.copy(prev_config, backup_config)

            if os.path.isfile(prev_config):
                os.remove(prev_config)
            assert cli.main() == 1

            if os.path.isfile(backup_config):
                shutil.copy(backup_config, prev_config)
            with patch.object(
                sys, 'argv', ['', '--forceDate', 'not a date']
            ):
                cli.main()
            exception_value = 'Invalid forceDate format, use "YYYY-mm-dd"'
            assert exception_value in caplog.text

            # Clean-up
            if os.path.isfile(backup_config):
                shutil.copy(backup_config, prev_config)
            for sample_user in sample_users:
                sample_user_obj = sample_user['user_obj']
                for t_user in sample_user_obj.twitter_username:
                    idx = sample_user_obj.twitter_username.index(t_user)
                    pinned_path = os.path.join(
                        os.getcwd(),
                        'users',
                        sample_user_obj.twitter_username[idx],
                        'pinned_id.txt'
                    )
                    pinned_pleroma = os.path.join(
                        os.getcwd(),
                        'users',
                        sample_user_obj.twitter_username[idx],
                        'pinned_id_pleroma.txt'
                    )
                    if os.path.isfile(pinned_path):
                        os.remove(pinned_path)
                    if os.path.isfile(pinned_pleroma):
                        os.remove(pinned_pleroma)
                    # Restore config
                    if os.path.isfile(backup_config):
                        shutil.copy(backup_config, prev_config)
        mock.reset_mock()
    assert 'Exception occurred\nTraceback' in caplog.text


def test_post_pleroma_media_logger(rootdir, sample_users, caplog):
    test_user = UserTemplate()
    for sample_user in sample_users:
        with sample_user['mock'] as mock:
            sample_user_obj = sample_user['user_obj']
            if sample_user_obj.media_upload:
                test_files_dir = os.path.join(rootdir, 'test_files')
                sample_data_dir = os.path.join(
                    test_files_dir, 'sample_data'
                )

                media_dir = os.path.join(sample_data_dir, 'media')
                png = os.path.join(media_dir, 'image.png')
                svg = os.path.join(media_dir, 'image.svg')
                mp4 = os.path.join(media_dir, 'video.mp4')
                gif = os.path.join(media_dir, "animated_gif.gif")
                tweet_folder = os.path.join(
                    sample_user_obj.tweets_temp_path, test_user.pinned
                )
                os.makedirs(tweet_folder, exist_ok=True)
                shutil.copy(png, tweet_folder)
                shutil.copy(svg, tweet_folder)
                shutil.copy(mp4, tweet_folder)
                shutil.copy(gif, tweet_folder)

                media_url = (
                    f"{test_user.pleroma_base_url}/api/v1/media"
                )
                mock.post(media_url, status_code=413)
                with caplog.at_level(logging.ERROR):
                    sample_user_obj.post_pleroma(
                        (test_user.pinned, "", "", None, None), None, False
                    )
                assert 'Exception occurred' in caplog.text
                assert 'Media size too large' in caplog.text

                mock.post(media_url, status_code=500)
                with pytest.raises(
                        requests.exceptions.HTTPError
                ) as error_info:
                    sample_user_obj.post_pleroma(
                        (test_user.pinned, "", "", None, None), None, False
                    )
                exception_value = (
                    f"500 Server Error: None for url: {media_url}"
                )
                assert str(error_info.value) == exception_value

                error_json = {
                    "error": "Validation failed: File content type is "
                             "invalid, File is invalid "
                }
                mock.post(media_url, status_code=422, json=error_json)
                with caplog.at_level(logging.ERROR):
                    sample_user_obj.post_pleroma(
                        (test_user.pinned, "", "", None, None), None, False
                    )

                assert error_json["error"] in caplog.text

                for media_file in os.listdir(tweet_folder):
                    os.remove(os.path.join(tweet_folder, media_file))
                os.rmdir(tweet_folder)


def test_post_misskey_media_logger(rootdir, sample_users, caplog):
    test_user = UserTemplate()
    for sample_user in sample_users:
        with sample_user['mock'] as mock:
            sample_user_obj = sample_user['user_obj']
            sample_user_obj.instance = "misskey"
            if sample_user_obj.media_upload:
                test_files_dir = os.path.join(rootdir, 'test_files')
                sample_data_dir = os.path.join(
                    test_files_dir, 'sample_data'
                )

                media_dir = os.path.join(sample_data_dir, 'media')
                png = os.path.join(media_dir, 'image.png')
                svg = os.path.join(media_dir, 'image.svg')
                mp4 = os.path.join(media_dir, 'video.mp4')
                gif = os.path.join(media_dir, "animated_gif.gif")
                tweet_folder = os.path.join(
                    sample_user_obj.tweets_temp_path, test_user.pinned
                )
                os.makedirs(tweet_folder, exist_ok=True)
                shutil.copy(png, tweet_folder)
                shutil.copy(svg, tweet_folder)
                shutil.copy(mp4, tweet_folder)
                shutil.copy(gif, tweet_folder)

                media_url = (
                    f"{test_user.pleroma_base_url}/api/drive/files/create"
                )
                mock.post(media_url, json={}, status_code=413)
                with caplog.at_level(logging.ERROR):
                    sample_user_obj.post_misskey(
                        (test_user.pinned, "", "", None, None), None, False
                    )
                assert 'Exception occurred' in caplog.text
                assert 'Media size too large' in caplog.text

                mock.post(media_url, status_code=500)
                with pytest.raises(
                        requests.exceptions.HTTPError
                ) as error_info:
                    sample_user_obj.post_misskey(
                        (test_user.pinned, "", "", None, None), None, False
                    )
                exception_value = (
                    f"500 Server Error: None for url: {media_url}"
                )
                assert str(error_info.value) == exception_value

                error_json = {
                    "error": "Validation failed: File content type is "
                             "invalid, File is invalid "
                }
                mock.post(media_url, status_code=422, json=error_json)
                with caplog.at_level(logging.ERROR):
                    sample_user_obj.post_misskey(
                        (test_user.pinned, "", "", None, None), None, False
                    )

                assert error_json["error"] in caplog.text

                for media_file in os.listdir(tweet_folder):
                    os.remove(os.path.join(tweet_folder, media_file))
                os.rmdir(tweet_folder)


def test_post_pleroma_media_size_logger(
        rootdir, mock_request, sample_users, caplog):
    test_user = UserTemplate()

    with mock_request['mock'] as mock:
        users_file_size = get_config_users('config_file_size.yml')

        for user_item in users_file_size['user_dict']:
            posts_ids = {}
            sample_user_obj = User(
                user_item, users_file_size['config'], os.getcwd(), posts_ids
            )
            for t_user in sample_user_obj.twitter_username:
                tweets_v2 = sample_user_obj._get_tweets("v2", t_user=t_user)
                assert tweets_v2 == mock_request['sample_data']['tweets_v2']
                tweet = sample_user_obj._get_tweets("v1.1", test_user.pinned)
                assert tweet == mock_request['sample_data']['tweet']
                tweets = sample_user_obj._get_tweets("v1.1")
                assert tweets == mock_request['sample_data']['tweets_v1']

                with caplog.at_level(logging.ERROR):
                    tweets_to_post = sample_user_obj.process_tweets(tweets_v2)
                if hasattr(sample_user_obj, "file_max_size"):
                    error_msg = (
                        f'Attachment exceeded config file size '
                        f'limit ({sample_user_obj.file_max_size})'
                    )
                    assert error_msg in caplog.text
                    assert 'File size: 1.45MB' in caplog.text
                    ignore = 'Ignoring attachment and continuing...'
                    assert ignore in caplog.text

                for tweet in tweets_to_post['data']:
                    # Clean up
                    tweet_folder = os.path.join(
                        sample_user_obj.tweets_temp_path, tweet["id"]
                    )
                    if os.path.isdir(tweet_folder):
                        for file in os.listdir(tweet_folder):
                            file_path = os.path.join(tweet_folder, file)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
    return mock


def test_get_instance_info_mastodon(global_mock, sample_users, caplog):
    test_user = UserTemplate()
    nodeinfo = {"software": {"name": "mastodon"}}
    for sample_user in sample_users:
        with sample_user['mock'] as mock:
            sample_user_obj = sample_user['user_obj']
            for t_user in sample_user_obj.twitter_username:
                sample_user_obj.display_name = {t_user: random_string(50)}
                mock.get(f"{test_user.pleroma_base_url}/nodeinfo/2.0",
                         json=nodeinfo,
                         status_code=200)
                rich_text_orig = False
                assert len(sample_user_obj.display_name[t_user]) == 50
                if hasattr(sample_user_obj, "rich_text"):
                    if sample_user_obj.rich_text:
                        rich_text_orig = True
                with caplog.at_level(logging.DEBUG):
                    sample_user_obj._get_instance_info()
                    sample_user_obj.mastodon_enforce_limits()
                assert 'Target instance is Mastodon...' in caplog.text
                if rich_text_orig:
                    log_msg_rich_text = (
                        "Mastodon doesn't support rich text. Disabling it..."
                    )
                    log_msg_display_name = (
                        "Mastodon doesn't support display names longer "
                        "than 30 characters, truncating it and trying again..."
                    )
                    assert log_msg_rich_text in caplog.text
                    assert log_msg_display_name in caplog.text
                    assert len(sample_user_obj.display_name[t_user]) == 30
                    assert sample_user_obj.max_post_length == 500


def test_get_instance_info_misskey(global_mock, sample_users, caplog):
    test_user = UserTemplate()
    max_post_length = 3500
    nodeinfo = {
        "software": {"name": "misskey"},
        "metadata": {"maxNoteTextLength": max_post_length}
    }
    for sample_user in sample_users:
        with sample_user['mock'] as mock:
            sample_user_obj = sample_user['user_obj']
            for t_user in sample_user_obj.twitter_username:
                sample_user_obj.display_name = {t_user: random_string(50)}
                mock.get(f"{test_user.pleroma_base_url}/nodeinfo/2.0",
                         json=nodeinfo,
                         status_code=200)
                with caplog.at_level(logging.DEBUG):
                    sample_user_obj._get_instance_info()
                assert 'Instance appears to be Misskey' in caplog.text
                assert sample_user_obj.max_post_length == max_post_length


def test_force_date_logger(sample_users, monkeypatch, caplog):
    for sample_user in sample_users:
        with sample_user['mock'] as mock:
            sample_user_obj = sample_user['user_obj']
            monkeypatch.setattr('builtins.input', lambda: "2020-12-30")
            with caplog.at_level(logging.DEBUG):
                date = sample_user_obj.force_date()
            assert date == '2020-12-30T00:00:00Z'
            msg = ("How far back should we retrieve tweets from the "
                   "Twitter account?")
            msg_2 = "Enter a date (YYYY-MM-DD):"
            msg_3 = (
                "[Leave it empty to retrieve *ALL* tweets or enter 'continue'"
            )
            msg_4 = (
                "if you want the bot to execute as normal (checking date of"
            )
            msg_5 = "last post in the Fediverse account)]"
            msgs = [msg, msg_2, msg_3, msg_4, msg_5]
            for msg in msgs:
                assert msg in caplog.text
    return mock
