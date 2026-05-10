import React from 'react';
import { Modal, View, Text, TouchableOpacity, StyleSheet } from 'react-native';

interface Props {
  message: string;
  onYes: () => void;
  onNo: () => void;
}

export default function ReminderModal({ message, onYes, onNo }: Props) {
  return (
    <Modal transparent animationType="fade">
      <View style={styles.overlay}>
        <View style={styles.card}>
          <Text style={styles.message}>{message}</Text>
          <View style={styles.buttons}>
            <TouchableOpacity style={[styles.btn, styles.no]} onPress={onNo}>
              <Text style={styles.btnText}>No</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.btn, styles.yes]} onPress={onYes}>
              <Text style={styles.btnText}>Yes</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '80%',
    gap: 20,
  },
  message: {
    fontSize: 16,
    textAlign: 'center',
    color: '#1a1a1a',
  },
  buttons: {
    flexDirection: 'row',
    gap: 12,
  },
  btn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  yes: { backgroundColor: '#4CAF50' },
  no:  { backgroundColor: '#e53935' },
  btnText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
});
