@admin.command()
@check_bound_text()
async def setup(ctx):
        """ Performs vanilla server set up - can be tailored. """
        setup_details = {}
        setup_file = "config/setup.json"

        # Load Settings
        if os.path.exists(setup_file):
            with open(setup_file) as read_setup_file:
                setup_details = json.load(read_setup_file)
        else:
            print(f"No settings file exists at {setup_file}. Using defaults.")
            setup_details = {
                "Superadmin": ["Superadmin", [123456789123456789]],
                "Moderators": ["Moderators", [123456789123456789, 123456789123456789]],
            }
            with open(setup_file, "w+"):
                json.dump(setup_details, setup_file)

        # Sanity Checks
        if "Superadmin" not in setup_details:
            # Should be RoleName and  list of user IDs to apply - generally just one user.
            setup_details["Superadmin"] = ["Superadmin", [123456789123456789]]
            save_settings(setup_file)

        if "Moderators" not in setup_details:
            # Should be RoleName and a list of user IDs to apply - multiple users preferably.
            setup_details["Moderators"] = ["Moderators", [123456789123456789]]
            save_settings(setup_file)
