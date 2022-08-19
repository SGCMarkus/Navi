# nsmb-bigarena.py

import calendar
from datetime import datetime, timedelta
import re

import discord
from discord.ext import commands

from database import errors, reminders, users
from resources import emojis, exceptions, functions, settings, strings


class NotSoMiniBossBigArenaCog(commands.Cog):
    """Cog that contains the not so mini boss and big arena detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id != settings.EPIC_RPG_ID: return
        if message.embeds:
            embed: discord.Embed = message.embeds[0]
            message_title = message_field0_value = message_field1_name = ''
            if embed.title: message_title = embed.title
            if embed.fields:
                message_field0_value = embed.fields[0].value
                if len(embed.fields) > 1:
                    message_field1_value = embed.fields[1].value

            search_strings = [
                '**minin\'tboss** event', #English minin'tboss
                '**big arena** event', #English big arena
                'evento **minin\'tboss**', #Spanish, Portuguese minin't boss
                'evento de **big arena**', #Spanish, Portuguese big arena
            ]
            search_strings_excluded = [
                'not registered', #English
                'sin registro', #Spanish
                'sem registro', #Portuguese
            ]
            if (any(search_string in message_title.lower() for search_string in search_strings)
                and all(search_string not in message_field1_value.lower() for search_string in search_strings_excluded)):
                user = await functions.get_interaction_user(message)
                slash_command = False if user is None else True
                if slash_command:
                    interaction = await functions.get_interaction(message)
                    if interaction.name.startswith('big'):
                        event = 'big-arena'
                    elif interaction.name.startswith('minintboss'):
                        event = 'minintboss'
                    else:
                        return
                else:
                    user_command_message, user_command = (
                        await functions.get_message_from_channel_history(
                            message.channel, r"^rpg\s+(?:big\b\s+arena\b|minintboss\b)", user
                        )
                    )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('Couldn\'t find a command for the big-arena or minin\'tboss embed.', message)
                        return
                    user = user_command_message.author
                if user is None:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User not found for the big-arena or minin\'tboss embed.', message)
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled: return
                if event == 'big-arena':
                    if not user_settings.alert_big_arena.enabled: return
                    reminder_message = user_settings.alert_big_arena.message.replace('{event}', event.replace('-',' '))
                if event == 'minintboss':
                    if not user_settings.alert_not_so_mini_boss.enabled: return
                    reminder_message = user_settings.alert_not_so_mini_boss.message.replace('{event}', event.replace('-',' '))
                search_patterns = [
                        r'in \*\*(.+?)\*\*', #English
                        r'en \*\*(.+?)\*\*', #Spanish
                        r'em \*\*(.+?)\*\*', #Portuguese
                    ]
                timestring_match = await functions.get_match_from_patterns(search_patterns, message_field0_value.lower())
                if not timestring_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Timestring not found in big arena / minintboss embed.', message)
                    return
                timestring = timestring_match.group(1)
                time_left = await functions.calculate_time_left_from_timestring(message, timestring)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, event, time_left,
                                                        message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)

        if not message.embeds:
            message_content = message.content
            search_strings = [
                'successfully registered for the next **big arena** event!', #English 1
                'successfully registered for the next **minin\'tboss** event!', #English 2
                'you are already registered!', #English 3
                'se registró exitosamente para el evento de **big arena**!', #Spanish 1
                'se registró exitosamente para el evento de **minin\'tboss**!', #Spanish 2
                'ya estás en registro!', #Spanish 3
                'inscreveu com sucesso no evento de **minin\'tboss**!', #Portuguese 1
                'inscreveu com sucesso no evento **big arena**!', #Portuguese 2
                'você já está em registro!', #Portuguese 3
            ]
            if any(search_string in message_content.lower() for search_string in search_strings):
                user_name = None
                user = await functions.get_interaction_user(message)
                slash_command = True if user is not None else False
                if user is None:
                    if message.mentions:
                        user = message.mentions[0]
                    else:
                        user_name_match = re.search(r"^\*\*(.+?)\*\*,", message_content)
                        if user_name_match:
                            user_name = await functions.encode_text(user_name_match.group(1))
                        else:
                            await functions.add_warning_reaction(message)
                            await errors.log_error('User not found in big-arena or minin\'tboss message.', message)
                            return
                        user = await functions.get_guild_member_by_name(message.guild, user_name)
                if user is None:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User not found in big-arena or minin\'tboss message.', message)
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled: return
                if slash_command:
                    interaction = await functions.get_interaction(message)
                    if interaction.name.startswith('big'):
                        user_command = '/big arena'
                    elif interaction.name.startswith('minintboss'):
                        user_command = '/minintboss'
                    else:
                        return
                    user_command = f'{user_command} join: true'
                else:
                    user_command_message, user_command = (
                            await functions.get_message_from_channel_history(
                                message.channel, r"^rpg\s+(?:big\s+arena|minintboss)\s+join\b", user
                            )
                        )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('Couldn\'t find a command for the big-arena or minin\'tboss message.', message)
                        return
                if 'minint' in user_command:
                    if not user_settings.alert_not_so_mini_boss.enabled: return
                    event = 'minintboss'
                    reminder_message = user_settings.alert_not_so_mini_boss.message.replace('{event}', event.replace('-',' '))
                else:
                    if not user_settings.alert_big_arena.enabled: return
                    event = 'big-arena'
                    reminder_message = user_settings.alert_big_arena.message.replace('{event}', event.replace('-',' '))
                search_patterns = [
                        r'next event is in \*\*(.+?)\*\*', #English
                        r'siguiente evento es en \*\*(.+?)\*\*', #Spanish
                        r'próximo evento (?:será|é) em \*\*(.+?)\*\*', #Portuguese
                    ]
                timestring_match = await functions.get_match_from_patterns(search_patterns, message_content.lower())
                if not timestring_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Timestring not found in big arena / minintboss message.', message)
                    return
                timestring = timestring_match.group(1)
                time_left = await functions.calculate_time_left_from_timestring(message, timestring)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, event, time_left,
                                                        message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)
                if reminder.record_exists:
                    if event == 'minintboss' and user_settings.alert_dungeon_miniboss.enabled:
                        if slash_command:
                            user_command = f"{strings.SLASH_COMMANDS['dungeon']} or {strings.SLASH_COMMANDS['miniboss']}"
                        else:
                            user_command = '`rpg dungeon` or `rpg miniboss`'
                        time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'dungeon-miniboss')
                        reminder_message = user_settings.alert_dungeon_miniboss.message.replace('{command}', user_command)
                        reminder: reminders.Reminder = (
                            await reminders.insert_user_reminder(user.id, 'dungeon-miniboss', time_left,
                                                                message.channel.id, reminder_message)
                        )
                    if event == 'big-arena' and user_settings.alert_arena.enabled:
                        if slash_command:
                            user_command = strings.SLASH_COMMANDS['arena']
                        else:
                            user_command = '`rpg arena`'
                        time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'arena')
                        reminder_message = user_settings.alert_arena.message.replace('{command}', user_command)
                        reminder: reminders.Reminder = (
                            await reminders.insert_user_reminder(user.id, 'arena', time_left,
                                                                message.channel.id, reminder_message)
                        )
                if user_settings.auto_ready_enabled: await functions.call_ready_command(self.bot, message, user)


# Initialization
def setup(bot):
    bot.add_cog(NotSoMiniBossBigArenaCog(bot))