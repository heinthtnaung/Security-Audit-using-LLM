"""Split an Ollama model name into its parts: registry, namespace, name and tag.

In `myregistry:5000/team/qwen2.5:7b` the tag `7b` is only ever in the last path
part, so a registry port's ":" is never read as a tag.
"""

PATH_SEPARATOR = "/"
TAG_SEPARATOR = ":"


def last_part(model: str) -> str:
    """Give the last part of a model's path: its own name, and its tag where it has one."""
    return model.rsplit(PATH_SEPARATOR, 1)[-1]


def family_of(model: str) -> str:
    """Guess a model's family from its own name, without its registry, namespace or tag."""
    return last_part(model).split(TAG_SEPARATOR, 1)[0]
