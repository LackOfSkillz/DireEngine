import argparse

from world.area_forge.run import run_area_forge


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", required=True)
    parser.add_argument("--area-id", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--profile", choices=["yaml_graph", "dr_city"], default="yaml_graph")
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--mode", choices=["extract", "review", "enrich", "build", "full"], default="full")
    args = parser.parse_args(argv)

    run_area_forge(
        args.map,
        args.area_id,
        mode=args.mode,
        manifest_path=args.manifest,
        use_ocr=not args.no_ocr,
        profile=args.profile,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

