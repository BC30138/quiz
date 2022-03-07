import argparse
import logging

import telegram
from telegram import Update
from telegram.ext import CallbackContext


class GameState:
    def __init__(self):
        self._host = None
        self._participants = []
        self._buzzers_on = False

    def get_buzzers_on(self):
        return self._buzzers_on

    def set_buzzers_on(self, buzzers_on):
        self._buzzers_on = buzzers_on

    def get_host(self):
        return self._host

    def set_host(self, host):
        self._host = host

    def get_participants(self):
        return self._participants

    def add_participant(self, participant):
        self._participants.append(participant)

    def get_all(self):
        return self._participants + [self._host]

GAME_STATE = GameState()


def get_person_name(participant_chat):
    name = ((participant_chat.first_name or '') + ' ' + (participant_chat.last_name or '')).strip()
    return name or participant_chat.username or participant_chat.title or '<без имени>'


HOST_GENERAL_MARKUP = telegram.InlineKeyboardMarkup([[telegram.InlineKeyboardButton('🔄', callback_data='host_action_buzzers_on'),
                                                      telegram.InlineKeyboardButton('❌', callback_data='host_action_game_over')]])
PARTICIPANT_GENERAL_MARKUP = telegram.InlineKeyboardMarkup([[telegram.InlineKeyboardButton('🔴', callback_data='participant_action_buzz')]])


def handle_inline_keyboard_default(update: Update, context: CallbackContext):
    logging.warning(f"Unknown inline keyboard button: {update.callback_query.data}.")


def handle_participant_action_buzz(update: Update, context: CallbackContext):
    if GAME_STATE.get_buzzers_on() and update.effective_chat in GAME_STATE.get_participants():
        GAME_STATE.set_buzzers_on(False)
        who_buzzed = update.effective_chat
        context.bot.send_message(who_buzzed.id, 'Ты отвечаешь первым!')
        context.bot.send_message(GAME_STATE.get_host().id, text=f"Отвечает {get_person_name(who_buzzed)}.", reply_markup=HOST_GENERAL_MARKUP)


def handle_host_action_game_over(update: Update, context: CallbackContext):
    global GAME_STATE
    if update.effective_chat == GAME_STATE.get_host():
        for person in GAME_STATE.get_all():
            context.bot.send_message(chat_id=person.id, text='Игра завершена!', reply_markup=telegram.ReplyKeyboardRemove())
        GAME_STATE = GameState()


def handle_host_action_buzzers_on(update: Update, context: CallbackContext):
    if update.effective_chat == GAME_STATE.get_host():
        GAME_STATE.set_buzzers_on(True)
        for person in GAME_STATE.get_participants():
            context.bot.send_message(chat_id=person.id, text='Баззеры включены!', reply_markup=PARTICIPANT_GENERAL_MARKUP)
        context.bot.send_message(chat_id=GAME_STATE.get_host().id, text='Баззеры включены!', reply_markup=HOST_GENERAL_MARKUP)


def handle_choose_role_participant(update: Update, context: CallbackContext):
    GAME_STATE.add_participant(update.effective_chat)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Это твой баззер. Нажимай, если знаешь ответ!', reply_markup=PARTICIPANT_GENERAL_MARKUP)
    if GAME_STATE.get_host():
        context.bot.send_message(chat_id=GAME_STATE.get_host().id, text=f"Участник {get_person_name(update.effective_chat)} вошёл в игру.", reply_markup=HOST_GENERAL_MARKUP)


def handle_choose_role_host(update: Update, context: CallbackContext):
    if GAME_STATE.get_host() is not None:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Ведущий уже есть. Ты - участник!')
        handle_choose_role_participant(update, context)
        return

    GAME_STATE.set_host(update.effective_chat)
    if GAME_STATE.get_participants():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"В игру уже вошли: {','.join(get_person_name(participant) for participant in GAME_STATE.get_participants())}.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"В игру пока никто не вошёл.")
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Нажми на 🔄, чтобы начать раунд. '
                                  'Первый баззер участника заблокирует остальные. '
                                  'После ответа участника нужно будет снова нажать 🔄, чтобы разрешить участникам использовать баззеры. '
                                  'Чтобы завершить игру, нажми ❌.',
                             reply_markup=HOST_GENERAL_MARKUP)


def handle_choose_role(update: Update, context: CallbackContext):
    buttons = [[telegram.InlineKeyboardButton('Я ведущий.', callback_data='choose_role_host')],
               [telegram.InlineKeyboardButton('Я участник.', callback_data='choose_role_participant')]]
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Какова твоя роль?',
                             reply_markup=telegram.InlineKeyboardMarkup(buttons))


def handle_start(update: Update, context: CallbackContext):
    if update.effective_chat not in GAME_STATE.get_all():
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Привет! Ты участвуешь в музыкальном квизе Образовательного Канала.',
                                 reply_markup=telegram.ReplyKeyboardRemove())
        if GAME_STATE.get_host() is not None:
            handle_choose_role_participant(update, context)
        else:
            handle_choose_role(update, context)


INLINE_KEYBOARD_HANDLERS = {
    'participant_action_buzz': handle_participant_action_buzz,
    'choose_role_host': handle_choose_role_host,
    'choose_role_participant': handle_choose_role_participant,
    'host_action_game_over': handle_host_action_game_over,
    'host_action_buzzers_on': handle_host_action_buzzers_on,
}

def handle_inline_keyboard(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer() # needed for some reason, otherwise some clients may have troubles
    INLINE_KEYBOARD_HANDLERS.get(query.data, handle_inline_keyboard_default)(update, context)


def create_bot(token: str):
    updater = telegram.ext.Updater(token=token, use_context='True')
    dispatcher = updater.dispatcher
    dispatcher.add_handler(telegram.ext.CommandHandler('start', handle_start))
    dispatcher.add_handler(telegram.ext.CallbackQueryHandler(handle_inline_keyboard))
    return updater


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    parser = argparse.ArgumentParser(description='Telegram bot for conducting music quizzes')
    parser.add_argument('-t', '--token', dest='token', type=str)
    args = parser.parse_args()

    bot = create_bot(args.token)
    bot.start_polling()
    bot.idle()
