import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Modal, View, Text, TouchableOpacity, StyleSheet, FlatList,
  NativeScrollEvent, NativeSyntheticEvent,
} from 'react-native';
import { colors, fonts, withAlpha } from '../theme/colors';

interface Props {
  visible: boolean;
  initialTime: string;
  onConfirm: (time: string) => void;
  onCancel: () => void;
  title?: string;
}

const ITEM_H = 52;
const VISIBLE = 5;
const PAD = Math.floor(VISIBLE / 2);
const WHEEL_H = ITEM_H * VISIBLE;

const HOURS_12 = ['12', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'];
const MINUTES = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'));
const PERIOD = ['AM', 'PM'];

function WheelColumn({
  data,
  selectedIndex,
  onIndexChange,
  visible,
  width,
}: {
  data: string[];
  selectedIndex: number;
  onIndexChange: (i: number) => void;
  visible: boolean;
  width: number;
}) {
  const listRef = useRef<FlatList>(null);
  const selectedIdxRef = useRef(selectedIndex);
  selectedIdxRef.current = selectedIndex;

  const paddedData = [...Array(PAD).fill(''), ...data, ...Array(PAD).fill('')];

  useEffect(() => {
    if (!visible) return;
    const t = setTimeout(() => {
      listRef.current?.scrollToOffset({
        offset: selectedIdxRef.current * ITEM_H,
        animated: false,
      });
    }, 50);
    return () => clearTimeout(t);
  }, [visible]);

  const handleScrollEnd = useCallback(
    (e: NativeSyntheticEvent<NativeScrollEvent>) => {
      const raw = e.nativeEvent.contentOffset.y / ITEM_H;
      const idx = Math.max(0, Math.min(data.length - 1, Math.round(raw)));
      onIndexChange(idx);
    },
    [data.length, onIndexChange],
  );

  return (
    <View style={[s.wheelOuter, { width }]}>
      <View style={s.selectionHighlight} pointerEvents="none" />
      <FlatList
        ref={listRef}
        data={paddedData}
        keyExtractor={(_, i) => String(i)}
        renderItem={({ item, index }) => {
          const di = index - PAD;
          const isSel = di === selectedIndex;
          const dist = Math.abs(di - selectedIndex);
          if (!item) return <View style={{ height: ITEM_H }} />;
          return (
            <View style={s.itemCell}>
              <Text
                style={[
                  s.itemText,
                  isSel ? s.selText : dist === 1 ? s.nearText : s.farText,
                ]}
              >
                {item}
              </Text>
            </View>
          );
        }}
        snapToInterval={ITEM_H}
        decelerationRate="fast"
        showsVerticalScrollIndicator={false}
        onMomentumScrollEnd={handleScrollEnd}
        onScrollEndDrag={handleScrollEnd}
        getItemLayout={(_, i) => ({ length: ITEM_H, offset: ITEM_H * i, index: i })}
        style={{ height: WHEEL_H }}
        bounces={false}
      />
    </View>
  );
}

export default function TimePickerModal({
  visible, initialTime, onConfirm, onCancel, title = 'Select Time',
}: Props) {
  const [hourIdx, setHourIdx] = useState(0);
  const [minIdx, setMinIdx] = useState(0);
  const [periodIdx, setPeriodIdx] = useState(0);

  useEffect(() => {
    if (!visible) return;
    if (initialTime && /^\d{1,2}:\d{2}/.test(initialTime)) {
      const [h, m] = initialTime.split(':').map(Number);
      const h24 = isNaN(h) ? 8 : Math.max(0, Math.min(23, h));
      setHourIdx(h24 % 12);
      setMinIdx(isNaN(m) ? 0 : Math.max(0, Math.min(59, m)));
      setPeriodIdx(h24 >= 12 ? 1 : 0);
    } else {
      const now = new Date();
      const h24 = now.getHours();
      setHourIdx(h24 % 12);
      setMinIdx(now.getMinutes());
      setPeriodIdx(h24 >= 12 ? 1 : 0);
    }
  }, [visible]);

  const h24 = (hourIdx % 12) + periodIdx * 12;
  const timeStr = `${String(h24).padStart(2, '0')}:${String(minIdx).padStart(2, '0')}`;
  const preview = `${HOURS_12[hourIdx]}:${String(minIdx).padStart(2, '0')} ${PERIOD[periodIdx]}`;

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <View style={s.overlay}>
        <View style={s.card}>
          <Text style={s.title}>{title}</Text>
          <Text style={s.preview}>{preview}</Text>

          <View style={s.wheelsRow}>
            <WheelColumn
              data={HOURS_12}
              selectedIndex={hourIdx}
              onIndexChange={setHourIdx}
              visible={visible}
              width={68}
            />
            <Text style={s.colonText}>:</Text>
            <WheelColumn
              data={MINUTES}
              selectedIndex={minIdx}
              onIndexChange={setMinIdx}
              visible={visible}
              width={68}
            />
            <WheelColumn
              data={PERIOD}
              selectedIndex={periodIdx}
              onIndexChange={setPeriodIdx}
              visible={visible}
              width={58}
            />
          </View>

          <View style={s.btnRow}>
            <TouchableOpacity onPress={onCancel} style={s.cancelBtn}>
              <Text style={s.cancelText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => onConfirm(timeStr)} style={s.doneBtn}>
              <Text style={s.doneText}>Done</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const s = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.52)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  card: {
    width: 310,
    backgroundColor: colors.white,
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.22,
    shadowRadius: 22,
    elevation: 14,
  },
  title: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
    marginBottom: 4,
  },
  preview: {
    fontSize: 30,
    fontFamily: fonts.extraBold,
    color: colors.primary,
    marginBottom: 16,
    letterSpacing: 1,
  },
  wheelsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 24,
  },
  wheelOuter: {
    height: WHEEL_H,
    overflow: 'hidden',
  },
  selectionHighlight: {
    position: 'absolute',
    left: 4,
    right: 4,
    top: PAD * ITEM_H,
    height: ITEM_H,
    backgroundColor: withAlpha(colors.primary, 0.1),
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: withAlpha(colors.primary, 0.22),
    zIndex: 1,
  },
  itemCell: {
    height: ITEM_H,
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemText: {
    fontSize: 18,
    fontFamily: fonts.regular,
    color: withAlpha(colors.textPrimary, 0.35),
  },
  selText: {
    fontSize: 28,
    fontFamily: fonts.extraBold,
    color: colors.primary,
  },
  nearText: {
    fontSize: 20,
    fontFamily: fonts.semiBold,
    color: withAlpha(colors.textPrimary, 0.6),
  },
  farText: {
    fontSize: 16,
    fontFamily: fonts.regular,
    color: withAlpha(colors.textPrimary, 0.2),
  },
  colonText: {
    fontSize: 26,
    fontFamily: fonts.extraBold,
    color: colors.textSecondary,
    paddingBottom: 4,
    marginHorizontal: 2,
  },
  btnRow: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
  },
  cancelBtn: {
    flex: 1,
    height: 46,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: withAlpha(colors.textMuted, 0.3),
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelText: {
    fontSize: 15,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
  },
  doneBtn: {
    flex: 1,
    height: 46,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  doneText: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.white,
  },
});
