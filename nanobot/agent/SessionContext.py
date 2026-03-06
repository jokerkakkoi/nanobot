from nanobot.agent.context import ContextBuilder

class SessionContextBuilder(ContextBuilder):

    def build_system_prompt(self, skill_names: list[str] | None = None,session: Session | None = None) -> str:
        """Build the system prompt from identity, bootstrap files, memory, and skills."""
        parts = [self._get_identity()]

        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)

        memory = self.memory.get_session_memory_context(session)

        if memory:
            parts.append(f"# Memory\n\n{memory}")

        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")

        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"""# Skills

    The following skills extend your capabilities. To use a skill, read its SKILL.md file using the read_file tool.
    Skills with available="false" need dependencies installed first - you can try installing them with apt/brew.

    {skills_summary}""")

        return "\n\n---\n\n".join(parts)



    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
        session: Session = None
    ) -> list[dict[str, Any]]:
        """Build the complete message list for an LLM call."""
        return [
            {"role": "system", "content": self.build_system_prompt(skill_names,session)},
            *history,
            {"role": "user", "content": self._build_runtime_context(channel, chat_id)},
            {"role": "user", "content": self._build_user_content(current_message, media)},
        ]