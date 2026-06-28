def test_platform_package_imports():
    import productagents.platform as platform

    assert platform.__name__ == "productagents.platform"
