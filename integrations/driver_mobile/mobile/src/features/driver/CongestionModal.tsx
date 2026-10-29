/**
 * CongestionModal component: one-tap incident reporting modal.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import { submitCongestionReport } from '../../api/reports';
import { SeverityLevel } from '../../api/types';
import { PrimaryButton } from '../../components/PrimaryButton';
import { CONSTANTS } from '../../config/constants';

interface CongestionModalProps {
  visible: boolean;
  baseRouteVersion: number;
  onClose: () => void;
  onSuccess: () => void;
}

export const CongestionModal: React.FC<CongestionModalProps> = ({
  visible,
  baseRouteVersion,
  onClose,
  onSuccess,
}) => {
  const [severity, setSeverity] = useState<SeverityLevel>('heavy');
  const [note, setNote] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      await submitCongestionReport(baseRouteVersion, severity, note);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit incident report');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.card}>
          <View style={styles.header}>
            <Text style={styles.title}>Report Traffic Congestion</Text>
            <Text style={styles.subtitle}>
              Triggers real-time server route re-evaluation and alternative corridor scoring.
            </Text>
          </View>

          <Text style={styles.label}>Select Incident Severity:</Text>
          <View style={styles.severityRow}>
            <TouchableOpacity
              style={[
                styles.severityBtn,
                severity === 'moderate' && styles.severityBtnSelectedModerate,
              ]}
              onPress={() => setSeverity('moderate')}
            >
              <Text style={styles.sevIcon}>⚠️</Text>
              <Text style={styles.sevTitle}>Moderate</Text>
              <Text style={styles.sevDelay}>+3 min (+180s)</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.severityBtn,
                severity === 'heavy' && styles.severityBtnSelectedHeavy,
              ]}
              onPress={() => setSeverity('heavy')}
            >
              <Text style={styles.sevIcon}>🛑</Text>
              <Text style={styles.sevTitle}>Heavy Gridlock</Text>
              <Text style={styles.sevDelay}>+8 min (+480s)</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>Optional Driver Note:</Text>
          <TextInput
            style={styles.textInput}
            placeholder="e.g. Mahipalpur flyover bottleneck"
            placeholderTextColor="#64748b"
            value={note}
            onChangeText={setNote}
            maxLength={200}
          />

          {error && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          <View style={styles.btnRow}>
            <PrimaryButton
              title="Cancel"
              variant="secondary"
              onPress={onClose}
              disabled={isSubmitting}
              style={styles.btnCancel}
            />
            <PrimaryButton
              title="Submit Report"
              variant="danger"
              onPress={handleSubmit}
              isLoading={isSubmitting}
              style={styles.btnSubmit}
            />
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.75)',
    justifyContent: 'flex-end',
  },
  card: {
    backgroundColor: CONSTANTS.COLORS.surface,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: CONSTANTS.COLORS.surfaceBorder,
  },
  header: {
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
    color: CONSTANTS.COLORS.textMain,
  },
  subtitle: {
    fontSize: 12,
    color: CONSTANTS.COLORS.textMuted,
    marginTop: 4,
    lineHeight: 18,
  },
  label: {
    fontSize: 13,
    fontWeight: '700',
    color: '#cbd5e1',
    marginTop: 12,
    marginBottom: 8,
  },
  severityRow: {
    flexDirection: 'row',
    gap: 12,
  },
  severityBtn: {
    flex: 1,
    backgroundColor: '#0c1322',
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#1e293b',
  },
  severityBtnSelectedModerate: {
    borderColor: CONSTANTS.COLORS.warning,
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
  },
  severityBtnSelectedHeavy: {
    borderColor: CONSTANTS.COLORS.danger,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
  },
  sevIcon: {
    fontSize: 22,
    marginBottom: 4,
  },
  sevTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: CONSTANTS.COLORS.textMain,
  },
  sevDelay: {
    fontSize: 11,
    color: CONSTANTS.COLORS.textMuted,
    marginTop: 2,
  },
  textInput: {
    backgroundColor: '#0c1322',
    borderWidth: 1,
    borderColor: '#1e293b',
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: CONSTANTS.COLORS.textMain,
    marginBottom: 16,
  },
  errorBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  errorText: {
    color: CONSTANTS.COLORS.danger,
    fontSize: 12,
    textAlign: 'center',
  },
  btnRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
  },
  btnCancel: {
    flex: 1,
  },
  btnSubmit: {
    flex: 2,
  },
});
