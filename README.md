# sysu-check-in

[![CI](https://github.com/undefined443/sysu-check-in/actions/workflows/ci.yml/badge.svg)](https://github.com/undefined443/sysu-check-in/actions/workflows/ci.yml)

A command-line client for completing SYSU check-in activities.

## Installation

Install the latest release from PyPI:

```bash
uv tool install sysu-check-in
```

## Usage

Save the JPEG face image to submit as `face.jpg`, then run:

```bash
sysu-check-in <student-id>
```

You can also supply a different image path:

```bash
sysu-check-in <student-id> --image <image-path>
```

The command prints the raw response from the last required submission. It exits with a non-zero status and an error message if the image is missing, the request fails, an activity is unavailable, or the service rejects a submission.

## Development

Install the Git hooks once:

```bash
uv run --group dev pre-commit install
```

Run the test suite and static checks with:

```bash
uv run --group dev pytest
uv run --group dev ruff check .
uv run --group dev pyright
```

## License

Distributed under the [MIT License](LICENSE).
