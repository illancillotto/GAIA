from app.services.nas_parsers import (
    parse_acl_output,
    parse_group_output,
    parse_passwd_output,
    parse_share_listing,
)


def test_parse_passwd_output_extracts_users() -> None:
    raw = "mrossi:x:1001:100:Mario Rossi:/var/services/homes/mrossi:/sbin/nologin\n"
    users = parse_passwd_output(raw)

    assert len(users) == 1
    assert users[0].username == "mrossi"
    assert users[0].source_uid == "1001"
    assert users[0].full_name == "Mario Rossi"


def test_parse_group_output_extracts_members() -> None:
    raw = "amministrazione:x:2001:mrossi,lbianchi\n"
    groups = parse_group_output(raw)

    assert len(groups) == 1
    assert groups[0].name == "amministrazione"
    assert groups[0].members == ["mrossi", "lbianchi"]


def test_parse_share_listing_extracts_share_names() -> None:
    shares = parse_share_listing("contabilita\nhr\n")

    assert [share.name for share in shares] == ["contabilita", "hr"]


def test_parse_acl_output_extracts_allow_and_deny_entries() -> None:
    raw = "allow: group:amministrazione:read,write\ndeny: user:ospite:read\n"
    acl_entries = parse_acl_output(raw)

    assert len(acl_entries) == 2
    assert acl_entries[0].effect == "allow"
    assert acl_entries[0].subject == "group"
    assert acl_entries[0].permissions == "amministrazione:read,write"
    assert acl_entries[1].effect == "deny"
    assert acl_entries[1].subject == "user"
