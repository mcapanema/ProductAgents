def test_package_imports():
    import importlib.metadata

    assert importlib.metadata.version("productagents") == "0.1.0"
