from rest_framework import renderers, status
import orjson


class OnyxJSONRenderer(renderers.JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into JSON, returning a bytestring.
        """
        render_data = {}
        if renderer_context:
            view = renderer_context["view"]
            status_code = renderer_context["response"].status_code

            if status.is_client_error(status_code):
                render_data["status"] = "fail"
                render_data["code"] = status_code
                render_data["messages"] = data

            elif status.is_server_error(status_code):
                render_data["status"] = "error"
                render_data["code"] = status_code
                render_data["messages"] = data

            else:
                render_data["status"] = "success"
                render_data["code"] = status_code

                if getattr(view, "paginator", None):
                    render_data["next"] = view.paginator.get_next_link()
                    render_data["previous"] = view.paginator.get_previous_link()

                render_data["data"] = data

        # return super().render(
        #     render_data,
        #     accepted_media_type=accepted_media_type,
        #     renderer_context=renderer_context,
        # )

        if render_data is None:
            return b""

        return orjson.dumps(render_data)
