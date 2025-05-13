from dagger import dag, function, object_type

@object_type
class Sandbox:
    @function
    async def run_code(self, language: str, code: str) -> str:
        """Builds and executes code. Returns stdout"""
        if language == "go" or language == "golang":
            return await (
                dag.container()
                .from_("golang:1.23-alpine")
                .with_workdir("/app")
                .with_new_file("/app/main.go", code)
                .with_exec(["go", "run", "main.go"])
            ).stdout()
        elif language == "python":
            return await (
                dag.container()
                .from_("python:3.13-alpine")
                .with_workdir("/app")
                .with_new_file("/app/main.py", code)
                .with_exec(["python", "main.py"])
            ).stdout()
        elif language == "js" or language =="javascript":
            return await (
                dag.container()
                .from_("node:22-alpine")
                .with_workdir("/app")
                .with_new_file("/app/main.js", code)
                .with_exec(["node", "main.js"])
            ).stdout()
        else:
            raise ValueError(f"Unsupported language: {language}")

    @function
    async def run_command(self, command: str) -> str:
        """Runs a shell command. Returns stdout"""
        return await (
            dag.container()
            .from_("alpine")
            .with_workdir("/app")
            .with_exec(["sh", "-c", command])
        ).stdout()
