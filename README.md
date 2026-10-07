# sysu-check-in

[![CI](https://github.com/undefined443/sysu-check-in/actions/workflows/ci.yml/badge.svg)](https://github.com/undefined443/sysu-check-in/actions/workflows/ci.yml)

A command-line client for completing SYSU check-in activities.

## Usage

Save the JPEG face image to submit as `face.jpg`, then run:

```bash
uvx sysu-check-in <student-id>
```

You can also supply a different image path:

```bash
uvx sysu-check-in <student-id> --image <image-path>
```

Add `-v` to log progress to stderr, or `-vv` for debug details such as request payloads, HTTP status codes, response bodies and tracebacks:

```bash
uvx sysu-check-in <student-id> -vv
```

The command submits the face image, confirms that the service has recorded the check-in, and prints the raw submission response.

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
