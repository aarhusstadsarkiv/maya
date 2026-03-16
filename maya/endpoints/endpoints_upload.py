from starlette.requests import Request
from starlette.responses import JSONResponse
from maya.core.logging import get_log
from maya.core.auth import is_authenticated
import os
import tempfile

log = get_log()


async def upload(request: Request):
    """
    Handle file uploads.
    Dummy upload to tempdir, e.g. /tmp on linux.
    """
    try:
        await is_authenticated(request, permissions=["employee"])

        form = await request.form()
        files: list = form.getlist("files")
        tmp_dir = tempfile.gettempdir()

        saved_files = []

        for file in files:
            file_path = os.path.join(tmp_dir, file.filename)

            with open(file_path, "wb") as f:
                f.write(await file.read())
                saved_files.append(file_path)

        return JSONResponse(content={"error": False, "files": saved_files})
    except Exception as e:
        return JSONResponse(content={"error": True, "message": str(e)})
