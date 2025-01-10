from domain.auth.request.signup_request import SignUpRequest


def create_dummy_user(number_of_nodes: int):
    dummy_users = [
        SignUpRequest(
            email=f"test{i}@gooroom.com",
            password="$2b$12$K4kuDTzku5n.xyXYd45lUODLIZH5FGHY7upzFAGie20nQkG8iTibS",
            tags=["string"],
            nickname=f"nickname{i}",
            username=f"test{i}",
            profile_image_url="",
        )
        for i in range(1, number_of_nodes + 1)
    ]
    return dummy_users
